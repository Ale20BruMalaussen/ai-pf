
import numpy as np
import os
directory = 'C:\Users\aless\Desktop\dataset_AI_stablepower\transienti'
folders_spettri = ['spettri_pre_step', 'spettri_post_step']
nome_jaco = 'IEEE 39 fake grid forming_AC.npz'
n_channel = 2 #pre and post step
n_gen = 10
n_frequencies = 99 #choose based on frequency resolution

path_spettri_pre_step = []
path_spettri__poststep = []
path_list_pre_step = []
path_list_post_step = []
path_spettri_pre_step = os.path.join(directory,folders_spettri[0])
path_spettri_post_step = os.path.join(directory,folders_spettri[1])
for file in os.listdir(path_spettri_pre_step):
    path_list_pre_step.append(os.path.join(path_spettri_pre_step, file))
    path_list_post_step.append(os.path.join(path_spettri_post_step, file))
if len(path_list_pre_step) != len(path_list_post_step):
    print('warning diverso numero di path')

n_simu = len(path_list_pre_step)
tf = np.zeros((n_simu, n_channel, n_gen, n_frequencies))
step_array = np.zeros(n_simu)
Mtot_array = np.zeros(n_simu)
for i, (path_pre_step, path_post_step) in enumerate(zip(path_list_pre_step, path_list_post_step)):
    print(i)
    data_pre_step = np.load(path_pre_step, allow_pickle = True)
    data_post_step = np.load(path_post_step, allow_pickle = True)
    tf[i,0, :, :]= np.sum(data_pre_step['TF'], axis = 0).transpose() 
    tf[i, 1, :,:] = np.sum(data_post_step['TF'], axis = 0).transpose()
    Mtot_array[i] = data_pre_step['Mtot']
    Ta_no_step =[]
    Ta_step = []
    for k in data_pre_step['config'].item()['CIG'].keys():
        nested_k = list(data_pre_step['config'].item()['CIG'][k].keys())
        
        Ta_no_step.append(data_pre_step['config'].item()['CIG'][k][nested_k[0]]['Ta'])
        Ta_step.append(data_post_step['config'].item()['CIG'][k][nested_k[0]]['Ta'])
    step_array[i] = np.sum(np.array(Ta_step)-np.array(Ta_no_step))
    #step_array[i] = data_step['Mtot']- data_no_step['Mtot']


dataset = {'TF': tf, 'step': step_array, 'Mtot':Mtot_array}
np.savez_compressed('C:\\Users\\aless\\Desktop\\simu_transient\\spettri_noise_small_signal_analysis', **dataset)


