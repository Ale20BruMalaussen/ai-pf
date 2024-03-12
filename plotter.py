import numpy as np
import math
from matplotlib import pyplot as plt
import os
inertia_step = [100/3, 150/3, 200/3, 300/3, 400/3, 450/3, 500/3, 510/3]
path_base = 'C:\\Users\\aless\\Desktop\\inertia step simulations'
data = []
for i, step in enumerate(inertia_step):
    path = os.path.join(path_base, 'verifiche_'+ str(step), 'IEEE 39 fake grid forming_AC_TF_-4.0_1.0_100.npz')
    data.append(np.load(path, allow_pickle = True))


# Select the indeces with .speed for the generators
var_names = data[0]['var_names']
indeces = [i for i, s in enumerate(var_names) if '.speed' in s]

# Extract Transfer Function
def extract_tf(data):
    TF = data['TF'][0]
    TF = TF[:, indeces].transpose()
    # Take the absolute value of the transfer function
    TF = np.abs(TF)
    return TF
TF_list = []
for sim in data:
    TF_list.append(extract_tf(sim))

x = np.logspace(-4, 1, 501)
# Plotting
plt.figure(figsize=(10, 6))
data_original = np.load('C:\\Users\\aless\\Desktop\\inertia step simulations\\verifiche_2\\IEEE 39 fake grid forming_AC_TF_-4.0_1.0_100.npz', allow_pickle = True)
tf_or = extract_tf(data_original)
plt.semilogx(x, tf_or[4], lw = 5, label = 'original')
for i, item in enumerate(TF_list):
    plt.semilogx(x, item[7], label=str(inertia_step[i]*3))
plt.xlim((0.001,0.1))

# for i, spectrum in enumerate(TF):
#     spectrum = 20*np.log10(spectrum)
#     plt.semilogx(x, spectrum, label=f'Gen {i+1}')

plt.xlabel('Frequency (Hz)')
plt.ylabel('Magnitude dB')
plt.title('rotor speed spectral density')
plt.legend()
plt.grid(True, which="both", ls="--")
plt.show()
