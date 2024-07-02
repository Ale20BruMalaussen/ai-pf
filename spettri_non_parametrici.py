import numpy as np
import os
import sys
import scipy as sp
from matplotlib import pyplot as plt

path = 'C:\\Users\\aless\\Desktop\\simu_transient'

simu_name = 'IEEE39_stoch_CIG_tran.npz'
window_type = 'blackman'
path_simu = os.path.join(path, 'simu_step')
dir_spettri = os.path.join(path, 'spettri_'+ window_type + '_step')
frac_overlap = 0.7
start_stationariety = 200
t_start_tuple = (0, 200, 400, 600) #seconds
segment_time = 200 #sec
window_welch = 100 #sec
fs = 200 #Hz

Ta = (0.1, 0.1, 0.1) #s
N_CIG = 3

output = {}
missed = []
for simu_folder in os.listdir(path_simu):
    simu_file = os.path.join(path_simu, simu_folder, simu_name)
    try:
        data = np.load(simu_file, allow_pickle = True)
    except:
        missed.append(simu_folder)
        continue
    time_series =data['data'].item()['gen']['s:xspeed'][start_stationariety*fs :, :]
    #plt.plot(time_series)
    #plt.show()
    output['config'] = data['config']
    output['H'] = data['H']
    output['S'] = data['S']
    output['PF_with_slack'] = data['PF_with_slack']
    output['Ta'] = Ta
    output['N_CIG'] = N_CIG
    output['Mtot'] = data['momentum']
    print(simu_folder)
    for i,t_start in enumerate(t_start_tuple):
        (output['F'], output['TF']) = sp.signal.welch(time_series[t_start*fs : (t_start + segment_time)*fs, :], 
                                     axis = 0, 
                                     scaling = 'density', 
                                     fs = fs, 
                                     nperseg = window_welch*fs,
                                     window = window_type, 
                                     noverlap =frac_overlap*window_welch*fs,
                                     average = 'median')
        outfile = simu_folder + '_segment_{}_{}.npz'.format(i, window_type)
        np.savez_compressed(os.path.join(dir_spettri,outfile), **output)
print(missed)
    
        
        



