import os
import numpy as np
import json
from matplotlib import pyplot as plt
import scipy as sp
from scipy.signal import welch
import scipy.stats as ss
import re
from tqdm import tqdm

#import data
data = np.load("C:\\Users\\aless\\Desktop\\prova_non_param\\prova_piccolo_segnale\\simu_output\\jacobian_pre\\IEEE39_stoch_CIG_AC.npz", allow_pickle=True)
outdir = 'C:\\Users\\aless\\Desktop\\prova_non_param\\prova_piccolo_segnale\\spettri'
outfile = 'spettro_small_signal_pre'
#define parameters
#inject active or reactive power
use_P_constraint = True
use_Q_constraint = False
T = 450
dt = 0.005
dP = [0.01] #injected power
dQ = None
sigmaP = None
sigmaQ = None


load_names = ['Load 03']
tau = 20e-3 #time constant of ornstein-uhlenbeck process

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

###########################################################################################
################ COMPUTATIONS #############################################################
###########################################################################################

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

#Find the bus connected to the loads
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

f_tot, PSD_tot = welch(OU_processes[:,50:], axis = 1, scaling = 'density', fs = 1/dt, nperseg = 1/dt*100,  window = 'hamming', noverlap =None, average = 'mean')
c = std_array[0]*np.sqrt(2/tau)
# PSD_th = 2*(c/alpha[0])**2 / (1 + (2*np.pi*f_tot/alpha[0])**2)

# plt.semilogx(f_tot, 10*np.log10(PSD_tot[0,:]), label ='estimated')
# plt.semilogx(f_tot, 10*np.log10(PSD_th), ls = '--', label = 'theory')
# plt.xlabel('F [hz]')
# plt.ylabel('dB10')
# plt.title('PSD theory and estimation')
# plt.show()

F = f_tot[(f_tot>0) & (f_tot<1)]
N_freq = len(F)
PSD = PSD_tot[:, (f_tot>0) & (f_tot<1)]
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
out = {'A': A, 'F': F, 'TF': TF,
        'var_names': var_names, 'SM_names': SM_names, 'bus_names': bus_names,
        'Htot': Htot, 'Etot': Etot, 'Mtot': Mtot, 'H': H, 'S': S, 'P': P, 'Q': Q,
        'PF': data['PF_without_slack'], 'bus_equiv_terms': data['bus_equiv_terms']}
np.savez_compressed(os.path.join(outdir, outfile), **out)
