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
config_file = 'config\\IEEE39_AC_config.json'
config = json.load(open(config_file, 'r'))
for i in range(2,10):
    config['synch_mach']['G 0' + str(i)] = {'typ_id.h' : original_inertia['G 0' + str(i)]}
config['synch_mach']['G 10'] = {'typ_id.h' : original_inertia['G 10']}

config['outdir'] = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\verifiche'
out_config_file = 'C:\\Users\\aless\\Desktop\\inertia step simulations\\config_verifiche.json'
json.dump(config, open(out_config_file, 'w'), indent = 4)