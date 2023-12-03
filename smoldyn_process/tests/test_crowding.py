from smoldyn import Simulation


model_fp = 'smoldyn_process/models/model_files/minE_model.txt'

sim = Simulation.fromFile(model_fp)

species_names = [sim.getSpeciesName(index) for index in range(sim.count()['species'])]
species_names.remove('empty')

species_names = ['MinE']

sim.run(1, 1)

sim.addOutputData('molecules')

for name in species_names:
    dataname = f'{name}_data'
    sim.addOutputData(dataname)
    sim.addCommand(cmd=f'listmols3 {name} {dataname}', cmd_type='E')

sim.run(1, 1)


mol_data = {}
for name in species_names:
    dataname = f'{name}_data'
    data = sim.getOutputData(dataname)
    print(f'{name}: {data}')
    #mol_data[dataname] = data


print(mol_data)

