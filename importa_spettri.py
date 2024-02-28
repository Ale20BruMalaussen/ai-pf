import numpy as np

data = np.load("D:\\POLIMI\\AI stable power\\39 New England\\Prova\\39 Bus New England System_AC_TF_-6.0_2.0_100.npz")
print(data['TF'].shape)
print(data['var_names'])