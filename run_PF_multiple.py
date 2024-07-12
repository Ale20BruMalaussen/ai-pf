
import re
import os
import sys
import json
from time import time as TIME
import numpy as np
from numpy.random import RandomState, SeedSequence, MT19937
sys.path.append("C:\Program Files\\DIgSILENT\\PowerFactory 2023 SP5\\Python\\3.9")
from programmi_Linaro.pfcommon import OU, get_simulation_time, get_simulation_variables, \
    run_power_flow, parse_sparse_matrix_file, parse_Amat_vars_file, \
        parse_Jacobian_vars_file
import subprocess

############################################################################
#############              USER SET PATH                  ##################
config_path = r"C:\Users\aless\Desktop\dataset_AI_stablepower\small_experiments\confronto_spettri_gen_OOS\config_file"
outfolder_path = r"C:\Users\aless\Desktop\dataset_AI_stablepower\small_experiments\confronto_spettri_gen_OOS\simu_output"
for config in os.listdir(config_path):
    complete_path = os.path.join(config_path, config) 
    outfile_folder = os.path.join(outfolder_path, config[:-5])
    outfile = os.path.join(outfile_folder, 'IEEE39_stoch_CIG_AC.npz')
    if not os.path.isdir(outfile_folder):
            os.makedirs(outfile_folder)
    # Costruisce il comando completo
    command = "c:/Users/aless/Desktop/uni/Ai_stable_power/repository/ai-pf/stablepower/Scripts/python.exe " 'c:/Users/aless/Desktop/uni/Ai_stable_power/repository/ai-pf/run_PF.py' + ' AC -v 3 -o ' + outfile + ' ' + complete_path

    print(command)
    # Esegue il comando
    subprocess.run(command)