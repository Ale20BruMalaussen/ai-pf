import sys
sys.path.append("C:\\Program Files\\DIgSILENT\\PowerFactory 2023\\Python\\3.11")
import powerfactory as pf

PF_APP = pf.GetApplication()
if PF_APP is None:
    print('\nCannot get PowerFactory application.')
else: 
    print('evviva')
    PF_APP.ResetCalculation()