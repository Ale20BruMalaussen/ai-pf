import json
import numpy as np
import random
import os
random.seed(42)
set_type = [1, 2, 3] #1 : low, 2 : medium, 3 : high


add_step =  True #metti true per fare le simulazioni con lo step
original_inertia = {'G 02': 4.33,
                    'G 03': 4.47,
                    'G 04': 3.57,
                    'G 05': 4.33,
                    'G 06': 4.35,
                    'G 07': 3.77,
                    'G 08': 3.47,
                    'G 09': 3.45,
                    'G 10': 4.20}
mother_path = 'C:\\Users\\aless\\Desktop\\inertia step simulations'
config_file = 'config\IEEE39_AC_config_grid_former.json'
out_path_base = os.path.join(mother_path, 'config_no_step')
out_path_step_base = os.path.join(mother_path, 'config_step')
outdir_base = os.path.join(mother_path, 'no_step')
outdir_step_base = os.path.join(mother_path, 'step')
config = json.load(open(config_file, 'r'))

def generate_limits(set):
    if set == 1:
        limits = (0.5, 0.8)
    elif set == 2:
        limits = (0.8, 1.25)
    else:
        limits = (1.25, 2)
    return limits

def define_number_simulations(set_1, set_2, set_3):
    somma = set_1 + set_2 + set_3
    if somma == 3 or somma == 9:
        n = 700
    elif somma == 4 or somma == 8:
        n = 200
    elif somma == 5 or somma == 6 or somma == 7:
        n = 100
    return n

def set_inertia(original_inertia, values_1, values_2, values_3, config):
    new_inertia = {}
    for i in range(2,10):
        if i==2 or i==3:
            factor = values_1 
        elif i>3 and i<8:
            factor = values_2
        else:
            factor = values_3
        config['synch_mach']['G 0' + str(i)] = {'typ_id.h' : original_inertia['G 0' + str(i)]*factor}
    config['synch_mach']['G 10'] = {'typ_id.h' : original_inertia['G 10'] * values_3}
    config['synch_mach']['Power Plant 11'] = {'typ_id.h': 1}
    return config

if not add_step:
    for set_1 in set_type:
        interval_1 = generate_limits(set_1)
        for set_2 in set_type:
            interval_2 = generate_limits(set_2)
            for set_3 in set_type:
                interval_3 = generate_limits(set_3)
                n_sim = define_number_simulations(set_1, set_2, set_3)

                for sim in range(n_sim):
                    values_1 = random.uniform(interval_1[0], interval_1[1])
                    values_2 = random.uniform(interval_2[0], interval_2[1])
                    values_3 = random.uniform(interval_3[0], interval_3[1])
                    name_file =  '_' +str(set_1)+'_'+str(set_2)+'_'+str(set_3)+'_'+str(sim)
                    name_file_ext = name_file + '.json'
                    config = set_inertia(original_inertia, values_1, values_2, values_3, config)
                    config['outdir'] = os.path.join(outdir_base, name_file)
                    out_config_file = os.path.join(out_path_base, name_file_ext)
                    json.dump(config, open(out_config_file, 'w'), indent = 4)

else:
    lista_inertia =[]
    lista_file = os.listdir(os.path.join(mother_path, 'no_step'))
    for file in lista_file:
        path_file = os.path.join(mother_path, 'no_step', file, 'IEEE 39 fake grid forming_AC.npz')
        simu = np.load(path_file, allow_pickle = True)
        config = simu['config'].item()
        step_inertia = random.gauss(mu = 400, sigma = 100)
        if step_inertia<200:
            step_inertia = 200
        config['synch_mach']['Power Plant 11'] = {'typ_id.h': step_inertia/3}
        config['outdir'] = os.path.join(outdir_step_base, file)
        out_config_file = os.path.join(out_path_step_base, file + '.json')
        json.dump(config, open(out_config_file, 'w'), indent = 4)
        lista_inertia.append(step_inertia)

    with open(os.path.join(mother_path, 'inertia_step.txt'), 'w') as f:
        for file, inertia_value in zip(lista_file, lista_inertia):
            f.write(f"{file}; {inertia_value}\n")


                
            
            