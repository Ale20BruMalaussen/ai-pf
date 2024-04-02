import json
import numpy as np

data = np.load('C:\\Users\\aless\\Desktop\\inertia step simulations\\no_step\\_3_3_3_699\\IEEE 39 fake grid forming_AC_TF_-6.0_2.0_100.npz', allow_pickle = True)

print(data['TF'].shape)