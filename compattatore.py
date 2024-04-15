
import numpy as np
import os
directory = 'D:\\POLIMI\\AI stable power\\39 New England'
directory_spettri = os.path.join(directory, 'spettri no step')
lista_spettri = os.listdir(directory_spettri)
Hlist = []
matrice_totale = []
name_list = []

for i,spettro in enumerate(lista_spettri):
    path_spettro = os.path.join(directory_spettri, spettro)
    data = np.load(path_spettro, allow_pickle = True)
    matrice_totale.append(np.abs(data['TF'].transpose()))
    Hlist.append(data['Mtot'])
    name_list.append(spettro)
    print(i)

dataset = {}
dataset['TF'] = np.stack(matrice_totale, axis = 0)
print(dataset['TF'].shape)
dataset['Mtot'] = np.array(Hlist)
dataset['name'] = name_list
np.savez_compressed(os.path.join(directory, 'dataset_no_step'), **dataset)