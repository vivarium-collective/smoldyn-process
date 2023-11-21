from smoldyn import Simulation


model_fp = 'smoldyn_process/examples/model_files/crowding_model.txt'

sim = Simulation.fromFile(model_fp)

sim.addOutputData('listmols')
sim.addCommand(cmd='listmols', cmd_type='E')
sim.run(sim.stop, sim.dt)
data = sim.getOutputData('listmols', False)

# print(data)
# print(type(data))

