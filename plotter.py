import numpy as np
from matplotlib import pyplot as plt

data_low = np.load('D:\\POLIMI\AI stable power\\39 New England\\fake grid forming\\IEEE 39 fake grid forming_AC_TF_-4.0_1.0_100.npz',
                allow_pickle = True)

data_high = np.load('D:\POLIMI\AI stable power\\39 New England\\risultati fake grid forming alta inerzia\\IEEE 39 fake grid forming_AC_TF_-4.0_1.0_100.npz',
                allow_pickle = True) 




# Select the indeces with .speed for the generators
var_names = data_high['var_names']
indeces = [i for i, s in enumerate(var_names) if '.speed' in s]

# Extract Transfer Function
TF_low = data_low['TF'][0]
TF_low = TF_low[:, indeces].transpose()
# Take the absolute value of the transfer function
TF_low = np.abs(TF_low)

TF_high = data_high['TF'][0]
TF_high = TF_high[:, indeces].transpose()
# Take the absolute value of the transfer function
TF_high = np.abs(TF_high)

x = np.logspace(-4, 1, 501)
# Plotting
plt.figure(figsize=(10, 6))

spectrum_low = 20*np.log10(TF_low[6])
spectrum_high = 20*np.log10(TF_high[6])
plt.semilogx(x, spectrum_low, label=f'low')
plt.semilogx(x, spectrum_high, label=f'high')
plt.ylim((-170,-90))

# for i, spectrum in enumerate(TF):
#     spectrum = 20*np.log10(spectrum)
#     plt.semilogx(x, spectrum, label=f'Gen {i+1}')

plt.xlabel('Frequency (Hz)')
plt.ylabel('Magnitude dB')
plt.title('rotor speed spectral density')
plt.legend()
plt.grid(True, which="both", ls="--")
plt.show()
