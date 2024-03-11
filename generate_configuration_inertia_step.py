import json
import numpy as np
import random
random.seed(42)
set_type = [1, 2, 3] #1 : low, 2 : medium, 3 : high

original_inertia = {'G 02': 4.33,
                    'G 03': 4.47,
                    'G 04': 3.57,
                    'G 05': 4.33,
                    'G 06': 4.35,
                    'G 07': 3.77,
                    'G 08': 3.47,
                    'G 09': 3.45,
                    'G 10': 4.20}

config_file = 'config\\IEEE39_AC_config.json'
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
    return config

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
                config = set_inertia(original_inertia, values_1, values_2, values_3, config)
                config['outdir'] = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\no_step\\_'+str(set_1)+'_'+str(set_2)+'_'+str(set_3)+'_'+str(sim)
                out_config_file = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\config_no_step\\_'+str(set_1)+'_'+str(set_2)+'_'+str(set_3)+'_'+str(sim)+'.json'
                json.dump(config, open(out_config_file, 'w'), indent = 4)

            
          
         