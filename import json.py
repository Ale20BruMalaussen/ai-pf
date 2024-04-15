import json
import numpy as np

data = np.load('C:\\Users\\aless\\Desktop\\inertia_line\\simu no step\\_2.5\\IEEE 39 fake grid forming_AC.npz', allow_pickle = True)

print(data['momentum'])
