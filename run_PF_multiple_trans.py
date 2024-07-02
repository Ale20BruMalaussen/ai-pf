
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
config_path = "C:\\Users\\aless\\Desktop\\simu_transient\\configuration_files"

for config in os.listdir(config_path)[173:]:
    complete_path = os.path.join(config_path, config)
    # Costruisce il comando completo
    command = "c:/Users/aless/Desktop/uni/Ai_stable_power/repository/ai-pf/stablepower/Scripts/python.exe " 'c:/Users/aless/Desktop/uni/Ai_stable_power/repository/ai-pf/run_PF.py' + ' tran -v 3 ' + complete_path
    print(command)
    # Esegue il comando
    subprocess.run(command)