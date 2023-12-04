from smoldyn import Simulation
import json


model_fp = 'smoldyn_process/models/model_files/minE_model.txt'

sim = Simulation.fromFile(model_fp)

species_names = [sim.getSpeciesName(index) for index in range(sim.count()['species'])]
species_names.remove('empty')

species_names = ['MinE']

#sim.addOutputData('molecules')

#sim.addOutputData('molpos')

'''for name in species_names:
    dataname = f'{name}_data'
    sim.addOutputData(dataname)
    sim.addCommand(cmd=f'listmols3 {name} {dataname}', cmd_type='E')
'''


for spec in species_names:
    dataname = f'molPos_{spec}'
    sim.addOutputData(dataname)
    sim.addCommand(f'molpos {spec} {dataname}')

sim.run(1, 1)

pos_data = {}
for spec in species_names:
    dataname = f'molPos_{spec}'
    data = sim.getOutputData(dataname)
    pos_data[spec] = data


with open('outputs.json', 'w') as f:
    json.dump(pos_data, f, indent=4)



'''mol_data = {}
for name in species_names:
    dataname = f'{name}_data'
    data = sim.getOutputData(dataname)
    print(f'{name}: {data}')
    #mol_data[dataname] = data
'''

