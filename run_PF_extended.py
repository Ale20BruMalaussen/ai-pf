import re
import os
import sys
import json
from time import time as TIME
import numpy as np
from numpy.random import RandomState, SeedSequence, MT19937

from pfcommon import OU, get_simulation_time, get_simulation_variables, \
    run_power_flow, parse_sparse_matrix_file, parse_Amat_vars_file, \
        parse_Jacobian_vars_file


__all__ = ['compute_fourier_coeffs']

progname = os.path.basename(sys.argv[0])
sys.path.append("C:\Program Files\\DIgSILENT\\PowerFactory 2023 SP5\\Python\\3.9")
#C:\Program Files\DIgSILENT\PowerFactory 2023 SP5\Python\3.9
def compute_fourier_coeffs(F, time, speed, mu=10):
    n_F = len(F)
    n_generators = speed[0].shape[1]
    gammac = np.zeros((n_F, n_generators))
    gammas = np.zeros((n_F, n_generators))
    for i,(f,t,spd) in enumerate(zip(F, time, speed)):
        dt = np.diff(t)
        dt = dt[dt >= 1e-6][0]
        idx = t > t[-1] - mu / f
        for j in range(n_generators):
            gammac[i,j] = f/mu*dt*np.cos(2*np.pi*f*t[np.newaxis,idx]) @ (spd[idx,j]-1)
            gammas[i,j] = f/mu*dt*np.sin(2*np.pi*f*t[np.newaxis,idx]) @ (spd[idx,j]-1)
    return gammac,gammas


############################################################
###                   GLOBAL VARIABLES                   ###
############################################################

# the lists TO_TURN_ON and TO_TURN_OFF contain the objects that will have
# to be turned on and off at the end of the simulation
TO_TURN_ON = []
TO_TURN_OFF = []
# HVDCs contains the loads that model the HVDC connections in the Sardinia network 
HVDCs = []
# HVDC_P contains the default values of absorbed active powert of the HVDCs
HVDC_P = {}


############################################################
###                   UTILITY FUNCTIONS                  ###
############################################################


def _IC(dt, coiref=0, verbose=False):
    coirefs = {'element': 0, 'coi': 1, 'center_of_inertia': 1, 'nominal_frequency': 2}
    ### compute the initial condition of the simulation
    inc = PF_APP.GetFromStudyCase('ComInc')
    inc.iopt_sim = 'rms'
    inc.iopt_coiref = 2
    inc.tstart = 0
    inc.dtgrd = dt    # [s]
    if isinstance(coiref, str):
        if coiref not in coirefs:
            raise Exception('Accepted values for coiref are ' + ', '.join(coirefs.keys()))
        inc.iopt_coiref = coirefs[coiref]
    elif isinstance(coiref, int):
        if coiref not in (0,1,2):
            raise Exception('Accepted values for coiref are 0, 1, or 2')
        inc.iopt_coiref = coiref
    else:
        raise Exception('coiref must be a string or an integer')
    err = inc.Execute()
    if err:
        raise Exception('Cannot compute initial condition')
    elif verbose:
        print(f'Successfully computed initial condition (dt = {dt*1e3:.1f} ms).')
    return inc


def _tran(tstop, verbose=False):    
    ### run the transient simulation
    sim = PF_APP.GetFromStudyCase('ComSim')
    sim.tstop = tstop
    if verbose:
        sys.stdout.write('Running simulation until t = {:.1f} sec... '.format(tstop))
        sys.stdout.flush()
    t0 = TIME()
    err = sim.Execute()
    t1 = TIME()
    if verbose:
        sys.stdout.write(f'done in {t1-t0:.0f} sec.\n')
    return sim, t1-t0, err


def _get_objects(suffix, keep_out_of_service=False):
    return [obj for obj in PF_APP.GetCalcRelevantObjects(suffix) \
            if not obj.outserv or keep_out_of_service]


def _find_object(suffix, obj_name, in_service_only=True):
    for obj in _get_objects(suffix, not in_service_only):
        if obj.loc_name == obj_name:
            return obj
    return None


def _find_in_contents(container, obj_name):
    for obj in container.GetContents():
        if obj.loc_name == obj_name:
            return obj
    return None


def _activate_project(project_name, verbose=False):   
    ### Activate the project
    err = PF_APP.ActivateProject(project_name)
    print(project_name)
    if err:
        raise Exception(f'Cannot activate project {project_name}.')
    if verbose: print(f'Activated project "{project_name}".')
    ### Get the active project
    project = PF_APP.GetActiveProject()
    if project is None:
        raise Exception('Cannot get active project.')
    return project


def _find_objects(to_find, verbose=False):
    all_objs = []
    for dev_type,loc_names in to_find.items():
        objs = _get_objects('*.' + dev_type)
        for obj in objs:
            if obj.loc_name in loc_names:
                all_objs.append(obj)
                if verbose:
                    print(f'Found device `{obj.loc_name}`.')
    return all_objs


def _turn_on_off_objects(objs, outserv, verbose=False):
    for obj in objs:
        if obj.HasAttribute('outserv'):
            obj.outserv = outserv
            if verbose:
                print('Turned {} device `{}`.'.format('OFF' if outserv else 'ON', obj.loc_name))
        elif verbose:
            print('Device `{}` does not have an outserv attribute.'.format(obj.loc_name))
_turn_on_objects  = lambda objs, verbose=False: _turn_on_off_objects(objs, False, verbose)
_turn_off_objects = lambda objs, verbose=False: _turn_on_off_objects(objs, True, verbose)


def _find_SMs_to_toggle(synch_mach):
    in_service, out_of_service = [], []
    # synchronous machines that change their status
    SMs = [sm for sm in PF_APP.GetCalcRelevantObjects('*.ElmSym') \
           if sm.loc_name in synch_mach.keys() and sm.outserv == synch_mach[sm.loc_name]]
    if len(SMs) > 0:
        # substations
        substations = {obj.loc_name: substation for substation in \
                       PF_APP.GetCalcRelevantObjects('*.ElmSubstat') \
                       for obj in substation.GetContents() if obj in SMs}
        for name,substation in substations.items():
            for obj in substation.GetContents():
                if obj.HasAttribute('outserv'):
                    if obj.outserv:
                        out_of_service.append(obj)
                    else:
                        in_service.append(obj)
    return in_service, out_of_service


def _apply_configuration(config, verbosity_level):
    global TO_TURN_ON, TO_TURN_OFF, HVDCs, HVDC_P
    TO_TURN_ON = [obj for obj in _find_objects(config['out_of_service'], verbosity_level>1) \
                  if not obj.outserv]
    _turn_off_objects(TO_TURN_ON, verbosity_level>2)

    in_service = []
    if 'synch_mach' in config:
        SM_dict = {}
        for k,v in config['synch_mach'].items():
            if isinstance(v, int):
                SM_dict[k] = v
            elif isinstance(v, dict):
                SM = _find_object('*.ElmSym', k)
                if SM is not None:
                    for attr,value in v.items():
                        subattrs = attr.split('.')
                        obj = SM
                        for subattr in subattrs[:-1]:
                            obj = obj.GetAttribute(subattr)
                        obj.SetAttribute(subattrs[-1], value)
            else:
                raise Exception(f'Do not know how to deal with key `{k}` in config["synch_mach"]')
        in_service,TO_TURN_OFF = _find_SMs_to_toggle(SM_dict)
    TO_TURN_ON += in_service

    # switch off the objects that are currently in service
    _turn_off_objects(in_service)
    # switch on the objects that are currently out of service, i.e., they will
    # have to be turned off at the end
    _turn_on_objects(TO_TURN_OFF)

    # Run a power flow analysis
    PF1 = run_power_flow(PF_APP)
    P_to_distribute = 0
    slacks = []
    for SG in PF1['SGs']:
        if 'slack' in SG.lower():
            P_to_distribute += PF1['SGs'][SG]['P']
            slacks.append(_find_object('*.ElmGenStat', SG))
    if verbosity_level > 0: print(f'Total power to distribute from {len(slacks)} slack generators: {P_to_distribute:.2f} MW.')
    
    # Find the loads that model the HVDC connections
    HVDCs = [ld for ld in  _get_objects('ElmLod') if ld.typ_id.loc_name == 'HVDCload']
    idx = np.argsort([hvdc.plini for hvdc in HVDCs])[::-1]
    HVDCs = [HVDCs[i] for i in idx]
    HVDC_P = {hvdc.loc_name: hvdc.plini for hvdc in HVDCs}
    for hvdc in HVDCs:
        hvdc.plini = max(0., HVDC_P[hvdc.loc_name] - P_to_distribute)
        P_to_distribute -= HVDC_P[hvdc.loc_name] - hvdc.plini
        print('{}: {:.2f} -> {:.2f} MW'.format(hvdc.loc_name,
                                               HVDC_P[hvdc.loc_name],
                                               hvdc.plini))
        if P_to_distribute <= 1:
            break

    for slack in slacks:
        slack.outserv = True
        TO_TURN_ON.append(slack)
        
    PF2 = run_power_flow(PF_APP)
    for SM in PF1['SMs']:
        try:
            if verbosity_level > 0 and \
                (np.abs(PF1['SMs'][SM]['P'] - PF2['SMs'][SM]['P']) > 0.1 or \
                 np.abs(PF1['SMs'][SM]['Q'] - PF2['SMs'][SM]['Q']) > 0.1):
                print('{}: P = {:7.2f} -> {:7.2f} MW, Q = {:7.2f} -> {:7.2f} MVAr'.\
                      format(SM,
                             PF1['SMs'][SM]['P'],
                             PF2['SMs'][SM]['P'],
                             PF1['SMs'][SM]['Q'],
                             PF2['SMs'][SM]['Q']))
        except:
            pass

    return PF1, PF2


def _restore_network_state(verbose):
    global TO_TURN_ON, TO_TURN_OFF, HVDCs, HVDC_P
    for hvdc in HVDCs:
        hvdc.plini = HVDC_P[hvdc.loc_name]
    _turn_on_objects (TO_TURN_ON,  verbose)
    _turn_off_objects(TO_TURN_OFF, verbose)


def _compute_measures(fn, verbose=False):
    # synchronous machines
    cnt = 0
    Psm, Qsm = 0, 0
    H, S, J = {}, {}, {}
    for sm in PF_APP.GetCalcRelevantObjects('*.ElmSym'):
        if not sm.outserv:
            name = sm.loc_name
            Psm += sm.pgini
            Qsm += sm.qgini
            H[name],S[name] = sm.typ_id.h, sm.typ_id.sgn
            J[name],polepairs = sm.typ_id.J, sm.typ_id.polepairs
            cnt += 1
            if verbose:
                print('[{:2d}] {}: S = {:7.1f} MVA, H = {:5.2f} s, J = {:7.0f} kgm^2, polepairs = {}{}'.
                      format(cnt, sm.loc_name, S[name], H[name], J[name], polepairs, ' [SLACK]' if sm.ip_ctrl else ''))
            #num += H*S
            #den += S
        elif sm.ip_ctrl and verbose:
            print('{}: SM SLACK OUT OF SERVICE'.format(sm.loc_name))
    # static generators
    Psg, Qsg = 0, 0
    for sg in PF_APP.GetCalcRelevantObjects('*.ElmGenStat'):
        if not sg.outserv:
            Psg += sg.pgini
            Qsg += sg.qgini
        if sg.ip_ctrl and verbose:
            print('{}: SG SLACK{}'.format(sg.loc_name, ' OUT OF SERVICE' if sg.outserv else ''))
    # loads
    Pload, Qload = 0, 0
    for load in PF_APP.GetCalcRelevantObjects('*.ElmLod'):
        if not load.outserv:
            Pload += load.plini
            Qload += load.qlini
    Etot = np.sum([H[k]*S[k] for k in H])
    Stot = np.sum(list(S.values()))
    Htot = Etot / Stot
    Mtot = 2 * Etot / fn
    if verbose:
        print('  P load: {:8.1f} MW'.format(Pload))
        print('  Q load: {:8.1f} MVAr'.format(Qload))
        print('    P SM: {:8.1f} MW'.format(Psm))
        print('    Q SM: {:8.1f} MVAr'.format(Qsm))
        print('    P SG: {:8.1f} MW'.format(Psg))
        print('    Q SG: {:8.1f} MVAr'.format(Qsg))
        print('    Stot: {:8.1f} MVA'.format(Stot))
        print(' INERTIA: {:8.1f} s.'.format(Htot))
        print('  ENERGY: {:8.1f} MJ.'.format(Etot))
        print('MOMENTUM: {:8.1f} MJ s.'.format(Mtot))
    return Htot,Etot,Mtot,Stot,H,S,J,Pload,Qload,Psm,Qsm,Psg,Qsg


def _set_vars_to_save(record_map, verbose=False):
    ### tell PowerFactory which variables should be saved to its internal file
    # speed, electrical power, mechanical torque, electrical torque, terminal voltage
    res = PF_APP.GetFromStudyCase('*.ElmRes')
    device_names = {}
    if verbose: print('Adding the following quantities to the list of variables to be saved:')
    for dev_type in record_map:
        devices = _get_objects('*.' + dev_type)
        try:
            key = record_map[dev_type]['devs_name']
        except:
            key = dev_type
        device_names[key] = []
        for dev in devices:
            if (isinstance(record_map[dev_type]['names'], str) and \
                (record_map[dev_type]['names'] == '*' or \
                 re.match(record_map[dev_type]['names'], dev.loc_name) is not None)) or \
                dev.loc_name in record_map[dev_type]['names']:
                if verbose: sys.stdout.write(f'{dev.loc_name}:')
                for var_name in record_map[dev_type]['vars']:
                    res.AddVariable(dev, var_name)
                    if verbose: sys.stdout.write(f' {var_name}')
                device_names[key].append(dev.loc_name)
                if verbose: sys.stdout.write('\n')
    return res, device_names


def _get_attributes(record_map, verbose=False):
    device_names = {}
    attributes = {}
    ref_SMs = []
    if verbose: print('Getting the following attributes:')
    for dev_type in record_map:
        devices = _get_objects('*.' + dev_type)
        try:
            key = record_map[dev_type]['devs_name']
        except:
            key = dev_type
        device_names[key] = []
        attributes[key] = {}
        names = record_map[dev_type]['names']
        for dev in devices:
            if (isinstance(names,str) and \
                (names == '*' or re.match(names, dev.loc_name) is not None)) or \
               (isinstance(names,list) and dev.loc_name in names):
                if verbose: sys.stdout.write(f'{dev.loc_name}:')
                if 'attrs' in record_map[dev_type]:
                    for attr_name in record_map[dev_type]['attrs']:
                        if attr_name not in attributes[key]:
                            attributes[key][attr_name] = []
                        if '.' in attr_name:
                            obj = dev
                            for subattr in attr_name.split('.'):
                                obj = obj.GetAttribute(subattr)
                            attributes[key][attr_name].append(obj)
                        else:
                            attributes[key][attr_name].append(dev.GetAttribute(attr_name))
                        if verbose: sys.stdout.write(f' {attr_name}')
                device_names[key].append(dev.loc_name)
                if dev_type == 'ElmSym' and dev.ip_ctrl:
                    ref_SMs.append(dev.loc_name)
                if verbose: sys.stdout.write('\n')
    return attributes, device_names, ref_SMs


def _get_data(res, record_map, data_obj, interval=(0,None), dt=None, verbose=False):
    # data_obj is a PowerFactor DataObject used to create an IntVec object
    # where the column data will be stored. If it is None, the (much slower)
    # GetValue function will be used, which gets one value at a time from the
    # ElmRes object
    if verbose:
        sys.stdout.write('Loading data from PF internal file... ')
        sys.stdout.flush()
    vec = data_obj.CreateObject('IntVec') if data_obj is not None else None
    t0 = TIME()
    res.Flush()
    res.Load()
    t1 = TIME()
    if verbose:
        sys.stdout.write(f'in memory in {t1-t0:.0f} sec... ')
        sys.stdout.flush()
    time = get_simulation_time(res, vec, interval, dt)
    t2 = TIME()
    if verbose:
        sys.stdout.write(f'read time in {t2-t1:.0f} sec... ')
        sys.stdout.flush()
    data = {}
    for dev_type in record_map:
        devices = _get_objects('*.' + dev_type)
        if isinstance(record_map[dev_type]['names'], list):
            devices = [dev for dev in devices if dev.loc_name in record_map[dev_type]['names']]
        elif isinstance(record_map[dev_type]['names'], str) and \
            record_map[dev_type]['names'] != '*' and '*' in  record_map[dev_type]['names']:
            devices = [dev for dev in devices if re.match(record_map[dev_type]['names'], dev.loc_name) is not None]
        try:
            key = record_map[dev_type]['devs_name']
        except:
            key = dev_type
        data[key] = {}
        for var_name in record_map[dev_type]['vars']:
            data[key][var_name] = get_simulation_variables(res, var_name, vec,
                                                           interval, dt, app=PF_APP,
                                                           elements=devices)
    res.Release()
    t3 = TIME()
    if vec is not None:
        vec.Delete()
    if verbose:
        sys.stdout.write(f'read vars in {t3-t2:.0f} sec (total: {t3-t0:.0f} sec).\n')
    return np.array(time), data


def _get_seed(config):
    if 'seed' in config:
        return config['seed']
    import time
    return time.time_ns() % 5061983


def _get_random_state(config):
    seed = _get_seed(config)
    rs = RandomState(MT19937(SeedSequence(seed)))
    return rs,seed


def _print_network_info():
    ### Get some info over the network
    generators = _get_objects('*.ElmSym')
    lines = _get_objects('*.ElmLne')
    buses = _get_objects('*.ElmTerm')
    loads = _get_objects('*.ElmLod')
    transformers = _get_objects('*.ElmTr2')
    n_generators, n_lines, n_buses = len(generators), len(lines), len(buses)
    n_loads, n_transformers = len(loads), len(transformers)
    print(f'There are {n_generators} generators.')
    print(f'There are {n_lines} lines.')
    print(f'There are {n_buses} buses.')
    print(f'There are {n_loads} loads.')
    print(f'There are {n_transformers} transformers.')


def _send_email(subject, content, recipients=['daniele.linaro@polimi.it']):
    import smtplib
    from email.message import EmailMessage
    if isinstance(recipients, str):
        recipients = [recipients]
    username = 'danielelinaro@gmail.com'
    password = 'inyoicyukfhlqebz'
    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = subject
    msg['To'] = ', '.join(recipients)
    msg['From'] = username
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(username, password)
    smtp_server.sendmail(username, recipients, msg.as_string())
    smtp_server.quit()


############################################################
###                     CLASSES                          ###
############################################################


class TimeVaryingLoad(object):
    def __init__(self, load, app, grid, library_name, user_models_name, frame_name, outdir='.'):
        self.load = load
        self.app = app
        self.grid = grid
        self.meas_filepath = os.path.join(os.path.abspath(outdir),
                                          load.loc_name.replace(' ', '_') + '_PQ.dat')
        library = _find_in_contents(self.app.GetActiveProject(), library_name)
        if library is None:
            raise Exception('Cannot locate library')
        user_models = _find_in_contents(library, user_models_name)
        if user_models is None:
            raise Exception('Cannot locate user models')
        self.frame = _find_in_contents(user_models, frame_name)
        if self.frame is None:
            raise Exception('Cannot locate time-varying load frame')
        ld_name = load.loc_name.replace(' ', '_')
        self.meas_file = self.grid.CreateObject('ElmFile', 'meas_' + ld_name)
        self.meas_file.f_name = self.meas_filepath
        self.comp_model = self.grid.CreateObject('ElmComp', 'time_dep_' + ld_name)
        self.comp_model.typ_id = self.frame
        self.comp_model.SetAttribute('pelm', [self.meas_file, self.load])

    @classmethod
    def _write(cls, filename, tPQ, verbose=False):
        if verbose:
            sys.stdout.write(f'Writing load values to `{filename}`... ')
            sys.stdout.flush()
        with open(filename, 'w') as fid:
            fid.write('2\n')
            for row in tPQ:
                fid.write(f'{row[0]:.6f}\t{row[1]:.2f}\t{row[2]:.2f}\n')
        if verbose:
            sys.stdout.write('done.\n')

    def write_to_file(self, dt, P, Q, verbose=False):
        n_samples = P.size
        tPQ = np.zeros((n_samples, 3))
        tPQ[:,0] = dt * np.arange(n_samples)
        tPQ[:,1] = P
        tPQ[:,2] = Q
        TimeVaryingLoad._write(self.meas_filepath, tPQ, verbose)

    def clean(self, verbose=False):
        if verbose: print(f'Deleting measurement file `{self.meas_file.loc_name}`...')
        self.meas_file.Delete()
        if verbose: print(f'Deleting composite model `{self.comp_model.loc_name}`...')
        self.comp_model.Delete()


class SinusoidalLoad(TimeVaryingLoad):
    def __init__(self, load, app, grid, library_name, user_models_name, frame_name, outdir='.'):
        super().__init__(load, app, grid, library_name, user_models_name, frame_name, outdir)

    def write_to_file(self, dt, P, Q, F, n_samples, verbose=False):
        t = dt * np.arange(n_samples)
        super().write_to_file(dt, P[0] + P[1] * np.sin(2*np.pi*F*t),
                              Q[0] + Q[1] * np.sin(2*np.pi*F*t), verbose)

class NormalStochasticLoad(TimeVaryingLoad):
    def __init__(self, load, app, grid, library_name, user_models_name, frame_name, outdir='.', seed=None):
        super().__init__(load, app, grid, library_name, user_models_name, frame_name, outdir)
        self.seed = seed
        if seed is not None:
            self.rs = RandomState(MT19937(SeedSequence(seed)))
        else:
            self.rs = np.random

    def write_to_file(self, dt, P, Q, n_samples, verbose=False):
        super().write_to_file(dt,
                              P[0] + P[1] * self.rs.normal(size=n_samples),
                              Q[0] + Q[1] * self.rs.normal(size=n_samples),
                              verbose)

class OULoad(TimeVaryingLoad):
    def __init__(self, load, app, grid, library_name, user_models_name, frame_name, outdir='.', seed=None):
        super().__init__(load, app, grid, library_name, user_models_name, frame_name, outdir)
        self.seed = seed
        if seed is not None:
            self.rs = RandomState(MT19937(SeedSequence(seed)))
        else:
            self.rs = None

    def write_to_file(self, dt, P, Q, n_samples, tau, verbose=False):
        if np.isscalar(tau):
            tau = [tau, tau]
        super().write_to_file(dt,
                              OU(dt, P[0], P[1], tau[0], n_samples, random_state=self.rs),
                              OU(dt, Q[0], Q[1], tau[1], n_samples, random_state=self.rs),
                              verbose)

############################################################
###                   AC ANALYSIS                        ###
############################################################


def run_AC_analysis(config_folder, config_file):
    config_path = os.path.join(config_folder, config_file)
    def usage(exit_code=None):
        print(f'usage: {progname} AC [-f | --force] [-o | --outfile <filename>] [-v | --verbose <level>] config_file')
        if exit_code is not None:
            sys.exit(exit_code)
            
    force = False
    outfile = None
    verbosity_level = 0


    if not os.path.isfile(config_path):
        print('{}: {}: no such file.'.format(progname, config_path))
        sys.exit(1)
    config = json.load(open(config_path, 'r'))
    if 'coiref' not in config:
        config['coiref'] = 'nominal_frequency'

    try:
        outdir = os.path.join(input_outdir, config_file[:-5])
        if not os.path.isdir(outdir):
            os.mkdir(outdir)
    except:
        try:
            outdir = os.config['outdir']
            if not os.path.isdir(outdir):
                os.mkdir(outdir)
        except:
            outdir = '.'
        

    outfile = os.path.join(outdir, config['project_name'] + '_AC.npz')


    PF_db_name = config['db_name'] if 'db_name' in config else 'aless'
    project_name = '\\' + PF_db_name + '\\' + config['project_name']
    project = _activate_project(project_name, verbosity_level>0)
    #_print_network_info()

    # we can't use _find_object because grids do not have an .outserv flag
    found = False
    for grid in PF_APP.GetCalcRelevantObjects('*.ElmNet'):
        if grid.loc_name == config['grid_name']:
            if verbosity_level > 0:
                print('Found grid named `{}`.'.format(config['grid_name']))
            found = True
            break
    if not found:
        print('Cannot find a grid named `{}`.'.format(config['grid_name']))
        sys.exit(1)

    PF1, PF2 = _apply_configuration(config, verbosity_level)
    
    Htot,Etot,Mtot,Stot,H,S,J,Pload,Qload,Psm,Qsm,Psg,Qsg = \
        _compute_measures(grid.frnom, verbosity_level>0)
    
    inc = _IC(0.001, coiref=config['coiref'], verbose=verbosity_level>1)
    modal_analysis = PF_APP.GetFromStudyCase('ComMod')
    # modal_analysis.cinitMode          = 1
    modal_analysis.iSysMatsMatl       = 1
    modal_analysis.iEvalMatl          = 1
    modal_analysis.output_type        = 1
    modal_analysis.repBufferAndExtDll = 1
    modal_analysis.repConstantStates  = 1
    modal_analysis.dirMatl            = outdir
    sys.stdout.write('Running modal analysis... ')
    sys.stdout.flush()
    err = modal_analysis.Execute()

    _restore_network_state(verbosity_level>2)

    if err:
        print('ERROR!')
    else:
        sys.stdout.write('done.\nSaving data... ')
        sys.stdout.flush()
        ref_SMs = [sm.loc_name for sm in _get_objects('*.ElmSym') if sm.ip_ctrl]
        loads = _get_objects('*.ElmLod')
        load_buses, bus_equiv_terms = {}, {}
        for i,load in enumerate(loads):
            # the bus to which the load is directly connected
            bus = load.bus1.cterm
            # list of terminals that are equivalent to bus, i.e., those terminals
            # that are only connected via closed switchs or zero-length lines
            equiv_terms = bus.GetEquivalentTerminals()
            # get connected busbars
            busbars = [bb for bb in bus.GetConnectedMainBuses() if bb in equiv_terms]
            n_busbars = len(busbars)
            if n_busbars == 0:
                load_buses[load.loc_name] = bus.loc_name
            elif n_busbars == 1:
                load_buses[load.loc_name] = busbars[0].loc_name
                # this is probably not really necessary
                equiv_terms = busbars[0].GetEquivalentTerminals()
            else:
                raise Exception(f'Cannot figure out the bus ``{load.loc_name}`` is connected to.')
            # print('[{:03d}] {} -> {}'.format(i+1,load.loc_name,load_buses[load.loc_name]))
            equiv_terms_names = sorted([term.loc_name for term in equiv_terms])
            bus_equiv_terms[load_buses[load.loc_name]] = equiv_terms_names

        A = parse_sparse_matrix_file(os.path.join(outdir, 'Amat.mtl'))
        J = parse_sparse_matrix_file(os.path.join(outdir, 'Jacobian.mtl'))
        cols,var_names,model_names = \
            parse_Amat_vars_file(os.path.join(outdir,'VariableToIdx_Amat.txt'))
        vars_idx,state_vars,voltages,currents,signals = \
            parse_Jacobian_vars_file(os.path.join(outdir,'VariableToIdx_Jacobian.txt'))
        omega_col_idx, = np.where([name == 'speed' for name in var_names])
        gen_names = [os.path.splitext(os.path.basename(model_names[i]))[0] \
                     for i in omega_col_idx]
        data = {'config': config,
                'inertia': Htot,
                'energy': Etot,
                'momentum': Mtot,
                'Stot': Stot,
                'H': H, 'S': S, 'J': J,
                'Psm': Psm, 'Qsm': Qsm,
                'Psg': Psg, 'Qsg': Qsg,
                'Pload': Pload, 'Qload': Qload,
                'PF_with_slack': PF1,
                'PF_without_slack': PF2,
                'J': J, 'vars_idx': vars_idx,
                'state_vars': state_vars, 'voltages': voltages,
                'currents': currents, 'signals': signals,
                'A': A, 'var_names': var_names,
                'model_names': model_names,
                'omega_col_idx': omega_col_idx,
                'gen_names': gen_names,
                'load_buses': load_buses,
                'bus_equiv_terms': bus_equiv_terms,
                'ref_SMs': ref_SMs}
        np.savez_compressed(outfile, **data)
        print('done.')

if __name__ == '__main__':
    ### Get the PowerFactory PF_APPlication
    import powerfactory as pf
    global PF_APP
    PF_APP = pf.GetApplication()
    if PF_APP is None:
        print('\nCannot get PowerFactory application.')
        sys.exit(1)

    config_path = "C:\\Users\\aless\\Desktop\\dataset_AI_stablepower\\small_experiments\\confronto_spettri_gen_OOS\\config_file"
    input_outdir = "C:\\Users\\aless\\Desktop\\dataset_AI_stablepower\\small_experiments\\confronto_spettri_gen_OOS\\simu_output"
    simulation_list = os.listdir(config_path)
  
    i=0
    for sim in simulation_list:
        print(sim)
        PF_APP.ResetCalculation()
        run_AC_analysis(config_path, sim)
        print(i)
        i+=1
