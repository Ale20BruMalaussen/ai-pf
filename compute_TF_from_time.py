import numpy as np
import json
from matplotlib import pyplot as plt
from scipy.signal import welch
import os
import sys

#set input and output folder
simu_folder = r"C:\Users\aless\Desktop\dataset_AI_stablepower\transienti\simu_step"
outdir = r'C:\Users\aless\Desktop\dataset_AI_stablepower\transienti\spettri_post_step'
#set name of the jacobian npz
jacobian_name = 'IEEE39_stoch_CIG_tran.npz' #tutti i file npz hanno questo nome

T_discard = 180
T = 400 #tempo finestra
spectra_per_simulation = 2
dt = 0.005 #campionamento del rumore
fs = 200

#PSD estimation generation
fmin,fmax = 0.01, 1. #Hz
window_type = 'hamming'
window_time = 100 #seconds
overlap_seconds = 0.5*window_time #seconds
average_type = 'mean'


list_simulations = os.listdir(simu_folder) #crea una lista di tutte le simulazioni
progname = os.path.basename(sys.argv[0])
for sim in list_simulations:
    data_file =os.path.join(simu_folder, sim, jacobian_name)
    if not os.path.isfile(data_file):
        print(f'{progname}: {data_file}: no such file.')
        sys.exit(1)
    data = np.load(data_file, allow_pickle=True)
    config = data['config']
    for n in range(spectra_per_simulation):
        save_name = sim + '_' + str(n)+'.npz'
        T_start = T_discard + (T*n)
        time_serie = data['data'].item()['gen']['s:xspeed'][T_start*fs: (T_start+T)*fs,:]
        f_tot, PSD_tot = welch(time_serie, axis = 0, scaling = 'density', fs = 1/dt, nperseg = fs*T,  window = window_type, noverlap =overlap_seconds, average = average_type)
        F = f_tot[(f_tot>=fmin) & (f_tot<fmax)]
        N_freq = len(F)
        TF = PSD_tot[(f_tot>=fmin) & (f_tot<fmax), :]
        out = {'config': config, 'F':F, 'TF': TF, 'Mtot': data['momentum'], 'H': data['H'], 'S': data['S'],'PF': data['PF_without_slack']}
        np.savez_compressed(os.path.join(outdir, save_name), **out)


