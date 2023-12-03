from smoldyn import Simulation


model_fp = 'smoldyn_process/models/model_files/minE_model.txt'

sim = Simulation.fromFile(model_fp)
sim.run(1, 1)

'''sim.addOutputData('molecules')
sim.addCommand(cmd='listmols2 molecules', cmd_type='E')
sim.run(sim.stop, sim.dt)
data = sim.getOutputData('molecules')

print(data[0])'''

# print(data)
# print(type(data))

