import os
import sys
import numpy as np
import json
from matplotlib import pyplot as plt
import scipy as sp
from scipy.signal import welch
import scipy.stats as ss
import re
from tqdm import tqdm
################################################################################################################
##############################    USER SETTINGS    #############################################################
################################################################################################################

#set input and output folder
jacobian_folder = "C:\\Users\\aless\\Downloads\\Per Alessio\\jaco_step"
outdir = 'C:\\Users\\aless\\Downloads\\Per Alessio\\spettri_post_step'
#set name of the jacobian npz
jacobian_name = 'IEEE39_stoch_CIG_AC.npz' #tutti i file npz hanno questo nome

    #define parameters
#inject active or reactive power
use_P_constraint = True
use_Q_constraint = False
dP = [0.01] #injected power
dQ = []
sigmaP = []
sigmaQ = []

# OU process  
T = 450 #tempo simulazione rumore
dt = 0.005 #campionamento del rumore
load_names = ['Load 03', 'Load 21']
tau = 20e-3 #time constant of ornstein-uhlenbeck process

#PSD estimation generation
fmin,fmax = 0.01, 1. #Hz
window_type = 'hamming'
window_time = 100 #seconds
overlap_seconds = 0.5*window_time #seconds
average_type = 'mean'

####################################################################################
###########                      FUNCTIONS                         #################
####################################################################################
def try_append(dst, src, i):
    try: dst.append(src[i])
    except: pass
def fix_len(lst1, lst2):
    if len(lst1) == 1 and len(lst2) > 1:
        return lst1*len(lst2)
    return lst1
def OU(dt, mean, stddev, tau, N, random_state = None):
    """
    OU returns a realization of the Ornstein-Uhlenbeck process given its
    parameters.

    Parameters
    ----------
    dt : float
        Time step.
    mean : float
        Mean of the process.
    stddev : float
        Standard deviation of the process.
    tau : float
        Time constant of the autocorrelation function of the process.
    N : integer
        Number of samples.
    random_state : RandomState object, optional
        The object used to draw the random numbers. The default is None.

    Returns
    -------
    ou : array of length N
        A realization of the Ornstein-Uhlenbeck process with the above parameters.

    """
    const = 2 * stddev**2 / tau
    mu = np.exp(-dt / tau)
    coeff = np.sqrt(const * tau / 2 * (1 - mu**2))
    if random_state is not None:
        rnd = random_state.normal(size=N)
    else:
        rnd = np.random.normal(size=N)
    ou = np.zeros(N)
    ou[0] = mean
    for i in range(1, N):
        ou[i] = mean + mu * (ou[i-1] - mean) + coeff * rnd[i]
    return ou

############################################################################################################
######################## SPECTRUM GENERATION ###############################################################
############################################################################################################
progname = os.path.basename(sys.argv[0])
list_simulations = os.listdir(jacobian_folder) #crea una lista di tutte le simulazioni
for sim in list_simulations:
    data_file =os.path.join(jacobian_folder, sim, jacobian_name)
    if not os.path.isfile(data_file):
        print(f'{progname}: {data_file}: no such file.')
        sys.exit(1)
    
    if not use_P_constraint and not use_Q_constraint:
        print(f'{progname}: at least one of --P and --Q must be specified.')
        sys.exit(1)

    if use_P_constraint:
        if len(dP) == 0 and len(sigmaP) == 0:
            print(f'{progname}: either --dP or --sigmaP must be specified with --P.')
            sys.exit(1)
        elif len(dP) > 0 and len(sigmaP) > 0:
            print(f'{progname}: only one of --dP and --sigmaP can be specified.')
            sys.exit(1)
    if use_Q_constraint:
        if len(dQ) == 0 and len(sigmaQ) == 0:
            print(f'{progname}: either --dQ or --sigmaQ must be specified with --Q.')
            sys.exit(1)
        elif len(dQ) > 0 and len(sigmaQ) > 0:
            print(f'{progname}: only one of --dP and --sigmaP can be specified.')
            sys.exit(1)

    if fmin >= fmax:
        print(f'{progname}: fmin must be < fmax.')
        sys.exit(1)

    if load_names is None:
        print(f'{progname}: you must specify the name of at least one load where the signal is injected.')
        sys.exit(1) 

    data = np.load(data_file, allow_pickle=True)
    config = data['config']
    SM_names = [n for n in data['gen_names']]
    bus_names = [n for n in data['voltages'].item().keys()]
    H = np.array([data['H'].item()[name] for name in SM_names])
    S = np.array([data['S'].item()[name] for name in SM_names])
    PF = data['PF_without_slack'].item()
    n_SMs = len(SM_names)
    P,Q = np.zeros(n_SMs), np.zeros(n_SMs)
    for i,name in enumerate(SM_names):
        if name in PF['SMs']:
            key = name
        else:
            key = name + '____GEN_____'
        P[i] = PF['SMs'][key]['P']
        Q[i] = PF['SMs'][key]['Q']
        
    #define the submatrix and define the system
    J,A = data['J'], data['A']
    vars_idx = data['vars_idx'].item()
    state_vars = data['state_vars'].item()
    N_vars = J.shape[0]
    N_state_vars = np.sum([len(v) for v in state_vars.values()])
    N_algebraic_vars = N_vars - N_state_vars
    Jfx = J[:N_state_vars, :N_state_vars]
    Jfy = J[:N_state_vars, N_state_vars:]
    Jgx = J[N_state_vars:, :N_state_vars]
    Jgy = J[N_state_vars:, N_state_vars:]
    Jgy_inv = np.linalg.inv(Jgy)
    Atmp = Jfx - Jfy @ Jgy_inv @ Jgx
    assert np.all(np.abs(A-Atmp) < 1e-8)


    load_buses = data['load_buses'].item()
    all_load_names = []
    all_dP,all_dQ,all_sigmaP,all_sigmaQ = [],[],[],[]

    for i,load_name in enumerate(load_names):
        if '*' in load_name:
            for load in load_buses.keys():
                if re.match(load_name, load):
                    all_load_names.append(load)
                    try_append(all_dP, dP, i)
                    try_append(all_dQ, dQ, i)
                    try_append(all_sigmaP, sigmaP, i)
                    try_append(all_sigmaQ, sigmaQ, i)
        elif load_name not in load_buses:
            print(f'cannot find load `{load_name}`.')
        else:
            all_load_names.append(load_name)
            try_append(all_dP, dP, i)
            try_append(all_dQ, dQ, i)
            try_append(all_sigmaP, sigmaP, i)
            try_append(all_sigmaQ, sigmaQ, i)
    load_names = all_load_names
    dP,dQ,sigmaP,sigmaQ = all_dP,all_dQ,all_sigmaP,all_sigmaQ

    dP = fix_len(dP, load_names)
    dQ = fix_len(dQ, load_names)
    sigmaP = fix_len(sigmaP, load_names)
    sigmaQ = fix_len(sigmaQ, load_names)

    #compute parameters for the OU process
    PF_loads = data['PF_without_slack'].item()['loads']
    idx = []
    std_list,alpha = [], []
    for i,load_name in enumerate(load_names):
        keys = []
        bus_name = load_buses[load_name]
        if bus_name not in vars_idx:
            # we have to look through the equivalent terms of bus_name
            bus_equiv_terms = data['bus_equiv_terms'].item()
            for equiv_term_name in bus_equiv_terms[bus_name]:
                if equiv_term_name in vars_idx:
                    print('Load {} is connected to bus {}, which is not among the '.
                            format(load_name, bus_name) + 
                            'buses whose ur and ui variables are in the Jacobian, but {} is.'.
                            format(equiv_term_name))
                    bus_name = equiv_term_name
                    break
        if use_P_constraint:
            # real part of voltage
            idx.append(vars_idx[bus_name]['ur'])
            keys.append('P')
        if use_Q_constraint:
            # imaginary part of voltage
            idx.append(vars_idx[bus_name]['ui'])
            keys.append('Q')
        for key in keys:
            mean = PF_loads[load_name][key]
            if key == 'P':
                if len(dP) > 0:
                    stddev = dP[i] * abs(mean)
                else:
                    stddev = sigmaP[i]
            else:
                if len(dQ) > 0:
                    stddev = dQ[i] * abs(mean)
                else:
                    stddev = sigmaQ[i]
            std_list.append(stddev)
            alpha.append(1/tau)

    idx = np.array(idx) - N_state_vars
    std_array,alpha = np.array(std_list), np.array(alpha)
    B = -Jfy @ Jgy_inv
    C = -Jgy_inv @ Jgx

    #generate the estimated PSD of the input
    OU_processes = np.zeros((len(load_names), int(T/dt)))
    for i in range(len(load_names)):
        OU_processes[i,:] = OU(dt, 0, std_array[i], tau, int(T/dt))

    f_tot, PSD_tot = welch(OU_processes[:,50:], axis = 1, scaling = 'density', fs = 1/dt, nperseg = 1/dt*window_time,  window = window_type, noverlap =overlap_seconds, average = average_type)
   
    # c = std_array[0]*np.sqrt(2/tau)
    # PSD_th = 2*(c/alpha[0])**2 / (1 + (2*np.pi*f_tot/alpha[0])**2)
    # plt.semilogx(f_tot, 10*np.log10(PSD_tot[0,:]), label ='estimated')
    # plt.semilogx(f_tot, 10*np.log10(PSD_th), ls = '--', label = 'theory')
    # plt.xlabel('F [hz]')
    # plt.ylabel('dB10')
    # plt.title('PSD theory and estimation')
    # plt.show()

    F = f_tot[(f_tot>=fmin) & (f_tot<fmax)]
    N_freq = len(F)
    PSD = PSD_tot[:, (f_tot>=fmin) & (f_tot<fmax)]
    #initialize matrix that will hold the results
    N_inputs = std_array.size
    I = np.eye(N_state_vars)
    M = np.zeros((N_freq, N_state_vars, N_state_vars), dtype=complex)
    TF = np.zeros((N_inputs, N_freq, N_state_vars+N_algebraic_vars))

    #compute spectrum frequency by frequency
    for i in tqdm(range(N_freq), ascii=True, ncols=70):
        M[i,:,:] = np.linalg.inv(-A + 1j*2*np.pi*F[i]*I)
        MxB = M[i,:,:] @ B
        PSD_value = PSD[:, i]
        v = np.zeros(N_algebraic_vars, dtype=float)
        for j,psd in enumerate(PSD_value):
            v[idx[j]] = psd
        tmp = np.square(np.abs(MxB)) @ v
        TF[j,i,:N_state_vars] = tmp
        TF[j,i,N_state_vars:] = np.square(np.abs((C @ MxB) - Jgy_inv)) @ v
    TF[TF==0] = 1e-20 
    vars_idx = data['vars_idx'].item()
    var_names,idx = [],[]
    for k1,D in vars_idx.items():
        for k2,v_ in D.items():
            var_names.append(k1 + '.' + k2)
            idx.append(v_)
    var_names = [var_names[i] for i in np.argsort(idx)]

    Htot = data['inertia']
    Etot = data['energy']
    Mtot = data['momentum']
    interesting_variables = ['G 01.speed', 'G 02.speed', 'G 03.speed', 
                                 'G 04.speed', 'G 05.speed', 'G 06.speed', 
                                 'G 07.speed', 'G 08.speed', 'G 09.speed', 'G 10.speed']
    index = []
    var_to_save = []
    for var in var_names:
        if var in interesting_variables:
            index.append(True)
            var_to_save.append(var)
        else:
            index.append(False)
    TF = np.squeeze(TF)[:, :, index]
    out = {'config': config, 'A': A, 'F': F, 'TF': TF,
            'var_names': var_names, 'SM_names': SM_names, 'bus_names': bus_names,
            'Htot': Htot, 'Etot': Etot, 'Mtot': Mtot, 'H': H, 'S': S, 'P': P, 'Q': Q,
            'PF': data['PF_without_slack'], 'bus_equiv_terms': data['bus_equiv_terms']}
    np.savez_compressed(os.path.join(outdir, sim), **out)
