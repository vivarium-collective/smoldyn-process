from smoldyn_process.utils import SmoldynModel


model_fp = 'smoldyn_process/examples/model_files/minE_model.txt'

model = SmoldynModel(model_fp)

for i, v in enumerate(dir(model.simulation)):
    print(f'{i}: {v}')
    print()

specs = [model.simulation.getSpeciesName(i) for i in range(model.counts.get('species'))]
bounds = model.simulation.getBoundaries()

print(bounds)
# create boundaries dict, accounting for each agent:
i = len(bounds) - 1
boundaries_dict = {
    'low': [bounds[i - 1] for spec in specs],
    'high': [bounds[i] for spec in specs]
}

print(boundaries_dict)
