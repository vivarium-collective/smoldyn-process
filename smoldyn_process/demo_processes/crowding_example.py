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
        'animate': 'boolean',
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

        # Set the species

        # count the num species
        species_count = self.simulation.count()['species']

        # create a list of species objects
        self.species: List[sm.Species] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            species_object = sm.Species(
                simulation=self.simulation,
                name=species_name,
                state=self.config.get('molecules')[species_name].get('state')
            )
            self.species.append(species_object)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step...
            # ...to be removed when expandable compartment size is possible
        self.boundaries = self.simulation.getBoundaries()

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl_better')

    def initial_state(self) -> Dict[str, Dict[None]]:
        """Set the initial parameter state of the simulation. NOTE: Due to the nature of this model,
            Smoldyn assigns a random uniform distribution of integers as the initial coordinate (x, y, z)
            values for the simulation. As such, the `set_uniform` method will uniformly distribute
            the molecules according to a `highpos`[x,y] and `lowpos`[x,y] where high and low pos are
            the higher and lower bounds of the molecule spatial distribution.
        """
        state = {
            'molecules': {}
        }
        return state

    def set_uniform(self, name: str, config: Dict[str, Any]) -> None:
        """Add a distribution of molecules to the solution in
            the simulation memory given a higher and lower bound x,y coordinate.
            TODO: If pymunk expands the species compartment, account for
            expanding `highpos` and `lowpos`.

            Args:
                name:`str`: name of the given molecule.
                config:`Dict`: molecule state.
        """
        self.simulation.runCommand(f'killmol {name}')
        self.simulation.addSolutionMolecules(
            name,
            config.get('counts'),
            highpos=config.get('high'),
            lowpos=config.get('low'))

    def schema(self) -> Dict[str, Dict[str, Dict[str, Union[str, Dict[str, str]]]]]:
        """Return a dictionary of molecule names and the expected input/output schema at simulation
            runtime.
        """
        tuple_type = {'_type': 'tuple', '_apply': 'set'}
        return {
            'molecules': {
                mol_name: {
                    'coordinates': tuple_type,
                    'velocity': tuple_type,  # QUESTION: could the expected shape be: ((0,0), (1,4)) where: ((xStart, xStop), (yStart, yStop)) ie directional?
                    'mol_type': {'_type': 'string', '_apply': 'set'},
                    'counts': 'int',
                    'high': 'list[number, number]',
                    'low': 'list[number, number]',
                    'state': 'string'
                } for mol_name in self.species
            }
        }

    def update(self, state: Dict, interval: int) -> Dict:
        """Callback method to be evoked at each Process interval.

            Args:
                state:`Dict`: current state of the Smoldyn simulation, expressed as a `Dict` whose
                    schema matches that which is returned by the `self.schema()` API method.
                interval:`int`: timestep interval at which to provide the update as the output
                    of this method. NOTE: This update is iteratively called with the `Process` API.

            Returns:
                `Dict`: New state according to the update at interval
        """
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


# register the process above as the name passed in the first argument below
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
