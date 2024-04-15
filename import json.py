import json
import numpy as np
from matplotlib import pyplot as plt
data = np.load("D:\\POLIMI\\AI stable power\\39 New England\\Prova\\39 Bus New England System_AC_TF_-3.0_-1.0_100.npz", allow_pickle = True)

print(data['TF'].shape)
TF = data['TF'][0]
print(len(np.where((np.abs(TF)<0.0000000001).all(axis = 0))[0]))
for gen in range(TF.shape[1]):
    plt.plot(np.abs(TF[:,gen]))

plt.show()