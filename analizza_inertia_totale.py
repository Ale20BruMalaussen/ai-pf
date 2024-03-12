import numpy as np
import json
import os
from matplotlib import pyplot as plt

path = "C:\\Users\\aless\\Desktop\\inertia step simulations\\no_step"
inertia = []
i=0
for obj in os.listdir(path):
    file = os.path.join(path, obj, '39 Bus New England System_AC.npz')
    data = np.load(file, allow_pickle = True)
    inertia.append((data['inertia']*data['Stot']/30-(5*10000/30))*30/(data['Stot']-10000))
    if i%100==0:
        print(i)
    i+=1

plt.hist(inertia, bins='auto')
plt.show()