
import numpy as np
import os
directory = 'C:\\Users\\aless\\Desktop\\simu_transient'
folders_spettri = ['spettri_noise_jacobiani_matteo_pre', 'spettri_noise_jacobiani_matteo_post']
nome_jaco = 'IEEE 39 fake grid forming_AC.npz'
n_channel = 2 #pre and post step
n_gen = 10
n_frequencies = 99 #choose based on frequency resolution

path_spettri_no_step = []
path_spettri_step = []
path_list_no_step = []
path_list_step = []
path_spettri_no_step = os.path.join(directory,folders_spettri[0])
path_spettri_step = os.path.join(directory,folders_spettri[1])
for file in os.listdir(path_spettri_no_step):
    path_list_no_step.append(os.path.join(path_spettri_no_step, file))
    path_list_step.append(os.path.join(path_spettri_step, file))
if len(path_list_no_step) != len(path_list_step):
    print('warning diverso numero di path')

n_simu = len(path_list_no_step)
tf = np.zeros((n_simu, n_channel, n_gen, n_frequencies))
step_array = np.zeros(n_simu)
Mtot_array = np.zeros(n_simu)
for i, (path_no_step, path_step) in enumerate(zip(path_list_no_step, path_list_step)):
    print(i)
    data_no_step = np.load(path_no_step, allow_pickle = True)
    data_step = np.load(path_step, allow_pickle = True)
    tf[i,0, :, :]= np.sum(data_no_step['TF'], axis = 0).transpose() 
    tf[i, 1, :,:] = np.sum(data_step['TF'], axis = 0).transpose()
    Mtot_array[i] = data_no_step['Mtot']

    Ta_no_step =[]
    Ta_step = []
    # for k in data_no_step['config'].item()['CIG'].keys():
    #     nested_k = list(data_no_step['config'].item()['CIG'][k].keys())
        
    #     Ta_no_step.append(data_no_step['config'].item()['CIG'][k][nested_k[0]]['Ta'])
    #     Ta_step.append(data_no_step['config'].item()['CIG'][k][nested_k[0]]['Ta'])
    # step_array[i] = np.sum(np.array(Ta_step)-np.array(Ta_no_step))
    step_array[i] = data_step['Mtot']- data_no_step['Mtot']


dataset = {'TF': tf, 'step': step_array, 'Mtot':Mtot_array}
np.savez_compressed('C:\\Users\\aless\\Desktop\\simu_transient\\spettri_noise_small_signal_analysis', **dataset)


