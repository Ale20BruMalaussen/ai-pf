import json
import numpy as np
config_file = 'config\\IEEE39_AC_config.json'
config = json.load(open(config_file, 'r'))
value_G2 = config['synch_mach']['G 02']['typ_id.h']
value_G3 = 4.475
list_g2 = np.arange(value_G2/2, value_G2*2+0.1, 0.1)
list_g3 = np.arange(value_G3/2, value_G3*2+0.1, 0.1)
config['synch_mach']['G 03'] = {'typ_id.h' : 0}
print(config)
for hg2 in list_g2:
    config['synch_mach']['G 02']['typ_id.h'] = hg2
    for hg3 in list_g3:
        config['synch_mach']['G 03']['typ_id.h'] = hg3
        config['outdir'] = 'C:\\Users\\aless\\Desktop\\modal_analysis\\IEEE39\\default\\' + 'AC_Hg2_' + str(hg2)[:4] + '_Hg3_' + str(hg3)[:4] 
        out_config_file = 'config dataset\\AC_Hg2_' + str(hg2)[:4]  + '_Hg3_' + str(hg3)[:4]  + '.json'
        json.dump(config, open(out_config_file, 'w'), indent = 4)

