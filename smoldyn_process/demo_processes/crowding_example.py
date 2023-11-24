from typing import *
import numpy as np
import smoldyn as sm
from process_bigraph import Process, Composite, process_registry, types
from smoldyn_process.sed2 import pf


class SmoldynProcess(Process):
    """Smoldyn-based implementation of bi-graph process' `Process` API."""

    config_schema = {
        'model_filepath': 'string',
        'species': 'dict',
        'animate': 'boolean'
    }

    def __init__(self, config: Dict = None):
        super().__init__(config)

        # specify the model fp for clarity
        self.model_filepath = self.config.get('model_filepath')

        # enforce model filepath passing
        if not self.model_filepath:
            raise ValueError('The config requires a path to a Smoldyn model file.')

        # initialize the simulator from a Smoldyn model.txt file.
        self.simulation: sm.Simulation = sm.Simulation.fromFile(self.model_filepath)

        """# query the model file to ensure that the appropriate Smoldyn output commands are present
        if not query_model(self.model_filepath, 'cmd'):
            self.simulation.addOutputData('executiontime')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 executiontime', cmd_type='i')
            self.simulation.addOutputData('listmols')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 listmols', cmd_type='i')
        """

        # get the species names
        species_count = self.simulation.count()['species']
        self.species: List[str] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            self.species.append(species_name)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step
        self.boundaries = self.simulation.getBoundaries()

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl_better')

    def initial_state(self):
        """NOTE: Due to the nature of this model, Smoldyn assigns a random uniform distribution of
            integers as the initial coordinate (x, y, z) values for the simulation.
        """
        # create species dict of coordinates and initialize to None

        state = {
            'molecules': {}
        }
        return state

    def set_uniform(self, name, config):
        self.simulation.runCommand(f'killmol {name}')
        self.simulation.addSolutionMolecules(
            name,
            config.get('counts'),
            highpos=config.get('high'),
            lowpos=config.get('low'))

    def schema(self):
        tuple_type = {'_type': 'tuple', '_apply': 'set'}
        return {
            'molecules': {
                mol_name: {
                    'coordinates': tuple_type,
                    'velocity': tuple_type,  # QUESTION: could the expected shape be: ((0,0), (1,4)) where: ((xStart, xStop), (yStart, yStop)) ie directional?
                    'mol_type': {'_type': 'string', '_apply': 'set'},
                    'counts': 'int'
                } for mol_name in self.species
            }
        }

    def update(self, state, interval) -> Dict:
        molecules = state['molecules']
        for mol_name, mol_state in molecules.items():
            self.set_uniform(mol_name, mol_state)

        # run the simulation for a given interval
        self.simulation.run(
            stop=interval,
            dt=self.simulation.dt
        )

        # get the data, clear the buffer
        data = self.simulation.getOutputData('listmols', True)

        # get the final counts for the update
        final_counts = data[-1]
        molecules = {}
        for index, name in enumerate(self.species, 1):
            molecules[name] = int(final_counts[index]) - state['molecules'][name]
        return {'molecules': molecules}


process_registry.register('smoldyn_process', SmoldynProcess)


def test_process():
    """Test the smoldyn process using the crowding model."""

    # this is the instance for the composite process to run
    instance = {
        'smoldyn': {
            '_type': 'process',
            'address': 'local:smoldyn_process',
            'config': {
                'model_filepath': 'crowding_model.txt',
                'animate': False,
            },
            'wires': {
                'molecules': ['molecules_store'],
            }
        },
        'emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'ports': {
                    'inputs': {
                        'molecules': 'dict'
                    }
                }
            },
            'wires': {
                'inputs': {
                    'molecules': ['molecules_store'],
                }
            }
        }
    }

    # make the composite
    workflow = Composite({
        'state': instance
    })

    # run
    workflow.run(10)

    # gather results
    results = workflow.gather_results()
    print(f'RESULTS: {pf(results)}')


if __name__ == '__main__':
    test_process()
