import json
import numpy as np
import random
import os
random.seed(42)

mother_path = 'C:\\Users\\aless\\Desktop\\simu_transient'
config_file = 'config\\IEEE39_tran_config.json'
out_path_base = os.path.join(mother_path, 'configuration_files')
out_path_step_base = os.path.join(mother_path, 'configuration_files_step')
outdir_base = os.path.join(mother_path, 'simu_no_step')
outdir_step_base = os.path.join(mother_path, 'simu_step')
db_name =  "aless\\stoch" #put you user name, if you put the project inside some folder in power factory, put the complete path
project_name = "IEEE39_stoch_CIG"
tstop = 1000


config = json.load(open(config_file, 'r'))
config['db_name'] = db_name
config['project_name'] = project_name
config['tstop'] = tstop
original_inertia = {'G 02': 4.33,
                    'G 03': 4.47,
                    'G 04': 3.57,
                    'G 05': 4.33,
                    'G 06': 4.35,
                    'G 07': 3.77,
                    'G 08': 3.47,
                    'G 09': 3.45,
                    'G 10': 4.20}
for gen, val in original_inertia.items():
    config['synch_mach'][gen] = {'typ_id.h' : val}


list_inertia = np.linspace(2, 6, 250) 
print(list_inertia)

for i, val in enumerate(list_inertia):
    name_file = 'simu_{}'.format(i)

    config['synch_mach']['G 01'] = {'typ_id.h' : val}
    config['CIG']["VSM Bus 08"]["CM - Power Control VSG 08"]= {'Ta' : 0.1}
    config['CIG']["VSM Bus 14"]["CM - Power Control VSG 14"]= {'Ta' : 0.1}
    config['CIG']["VSM Bus 27"]["CM - Power Control VSG 27"]= {'Ta' : 0.1}
    config['outdir'] = os.path.join(outdir_base, name_file)
    out_config_file = os.path.join(out_path_base, name_file + '.json')
    json.dump(config, open(out_config_file, 'w'), indent = 4)

    step_inertia = random.gauss(mu = 400, sigma = 100)
    config['CIG']["VSM Bus 08"]["CM - Power Control VSG 08"]= {'Ta' : step_inertia/3.0}
    config['CIG']["VSM Bus 14"]["CM - Power Control VSG 14"]= {'Ta' : step_inertia/3.0}
    config['CIG']["VSM Bus 27"]["CM - Power Control VSG 27"]= {'Ta' : step_inertia/3.0}
    config['outdir'] = os.path.join(outdir_step_base, name_file)
    out_config_file = os.path.join(out_path_step_base, name_file+ '_step_{:.1f}'.format(step_inertia) + '.json')
    json.dump(config, open(out_config_file, 'w'), indent = 4)


