from smoldyn import Simulation
import json
from smoldyn_process.utils import get_output_molecule_ids, read_model_file_as_list
from smoldyn._smoldyn import MolecState


model_fp = 'smoldyn_process/models/model_files/minE_model.txt'
modelout_fp = 'smoldyn_process/models/model_files/minE_modelout.txt'

sim = Simulation.fromFile(model_fp)

species_names = [sim.getSpeciesName(index) for index in range(sim.count()['species'])]
species_names.remove('empty')

new_counts = {
    "0": {
        name: sim.getMoleculeCount(name, MolecState.all)
        for name in species_names
    }
}

for name in species_names:
    print(sim.getMoleculeCount(name, MolecState.all))

dataname = 'species_counts'
sim.addOutputData(dataname)
sim.addCommand(cmd=f'molcount {dataname}', cmd_type='E')
time_stop = 10
sim.run(time_stop, 1)
species_counts_list = sim.getOutputData(dataname, False)
species_counts = {}

for timestep in species_counts_list:
    time_index = int(timestep.pop(0))
    species_counts[time_index] = {
        name: timestep[i]
        for i, name in enumerate(species_names)
    }

print(new_counts)


'''print(len(serials), len(unique_serials))
print(unique_ids)
print(len(species_id), len(unique_ids))

print(len(data), len(mols))'''


'''unique_mol_ids = get_output_molecule_ids(modelout_fp)
all_mol_ids = get_output_molecule_ids(modelout_fp, unique=False)

print(f'Unique ids:\n{unique_mol_ids}')
print(f'spec names:\n{species_names}')'''
sim.runSim()

#sim.addOutputData('molecules')

#sim.addOutputData('molpos')

'''for name in species_names:
    dataname = f'{name}_data'
    sim.addOutputData(dataname)
    sim.addCommand(cmd=f'listmols3 {name} {dataname}', cmd_type='E')
'''


'''for spec in species_names:
    dataname = spec
    listmols_dataname = dataname + '_molecule_list'
    counts_dataname = dataname + '_counts'
    sim.addOutputData(listmols_dataname)
    sim.addOutputData(counts_dataname)

    # listmols for each spec (coords)
    sim.addCommand(f'listmols3 {spec} {listmols_dataname}', cmd_type='E')

    # get counts for each spec
    sim.addCommand(f'molcount {spec} {counts_dataname}', cmd_type='E')'''



'''pos_data = {}
for spec in species_names:
    dataname = spec
    listmols_dataname = dataname + '_molecule_list'
    counts_dataname = dataname + '_counts'
    listmols_data = sim.getOutputData(listmols_dataname)
    counts_data = sim.getOutputData(counts_dataname)
    pos_data[spec] = {
        'counts': counts_data,
        'mol_data': listmols_data
    }


with open('outputs.json', 'w') as f:
    json.dump(pos_data, f, indent=4)



mol_data = {}
for name in species_names:
    dataname = f'{name}_data'
    data = sim.getOutputData(dataname)
    print(f'{name}: {data}')
    #mol_data[dataname] = data
'''

