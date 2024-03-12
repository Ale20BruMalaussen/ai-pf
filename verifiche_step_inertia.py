import json
import numpy as np
original_inertia = {'G 02': 4.33,
                    'G 03': 4.47,
                    'G 04': 3.57,
                    'G 05': 4.33,
                    'G 06': 4.35,
                    'G 07': 3.77,
                    'G 08': 3.47,
                    'G 09': 3.45,
                    'G 10': 4.20}
config_file = 'config\\IEEE39_AC_config_grid_former.json'
config = json.load(open(config_file, 'r'))
for i in range(2,10):
    config['synch_mach']['G 0' + str(i)] = {'typ_id.h' : original_inertia['G 0' + str(i)]}
config['synch_mach']['G 10'] = {'typ_id.h' : original_inertia['G 10']}
inertia_step = [100/3, 150/3, 200/3, 300/3, 400/3, 450/3, 500/3, 510/3]
for step in inertia_step:
    config['synch_mach']['Power Plant 11'] = {'typ_id.h': step}
    config['outdir'] = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\verifiche_'+str(step)
    out_config_file = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\config_verifiche_' +str(step) +'.json'
    json.dump(config, open(out_config_file, 'w'), indent = 4)