from typing import *
import numpy as np
import smoldyn as sm
from process_bigraph import Process, Composite, process_registry, types
from smoldyn_process.sed2 import pf


class SmoldynProcess(Process):
    """Smoldyn-based implementation of bi-graph process' `Process` API."""

    config_schema = {
        'model_filepath': 'string',
        'boundaries': 'tuple[list[number, number], list[number, number]]',
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

        # TODO: Add a handler that checks if self.config.get('molecules') is None, and sets thru Python if not

        # count the num species
        species_count = self.simulation.count()['species']

        # create a list of species objects
        self.species_names: List[str] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            self.species_names.append(species_name)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step...
            # ...to be removed when expandable compartment size is possible:
        self.boundaries = self.config.get('boundaries') or self.simulation.getBoundaries()

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl_better')

    def initial_state(self) -> Dict[str, Dict]:
        """Set the initial parameter state of the simulation. NOTE: Due to the nature of this model,
            Smoldyn assigns a random uniform distribution of integers as the initial coordinate (x, y, z)
            values for the simulation. As such, the `set_uniform` method will uniformly distribute
            the molecules according to a `highpos`[x,y] and `lowpos`[x,y] where high and low pos are
            the higher and lower bounds of the molecule spatial distribution.

            NOTE: This method should provide an implementation of the structure denoted in `self.schema`.
        """

        # TODO: update for distribution!
        '''for spec in self.species:
            molecule = self.config['molecules'].get(spec)
            self.simulation.addMolecules(
                species=spec,
                number=molecule['count'],
                pos=molecule['coordinates']
            )'''

        species_dict = {}
        for name in self.species_names:
            species_dict[name] = self.get_initial_molecule_state(
                coordinates=(0.0, 0.0),
                velocity=(0.0, 0.0),
                count=0,
                state="soln"
            )


        # TODO: fill these with a default state with get initial mol state method
        state = {
            'molecules': species_dict
        }
        return state

    def get_initial_molecule_state(self, **mol_config) -> Dict:
        """Return a dict expressing a molecule's initial state.

            Kwargs:
                coordinates:`Tuple[float, float]`
                velocity:`Tuple[float, float]`
                count:`int`
                state:`str`
        """
        return {**mol_config}

    def set_uniform(self, name: str, config: Dict[str, Any]) -> None:
        """Add a distribution of molecules to the solution in
            the simulation memory given a higher and lower bound x,y coordinate. Smoldyn assumes
            a global boundary versus individual species boundaries.
            TODO: If pymunk expands the species compartment, account for
            expanding `highpos` and `lowpos`.

            Args:
                name:`str`: name of the given molecule.
                config:`Dict`: molecule state.
        """
        # get the boundaries
        low_bounds = self.boundaries[0]
        high_bounds = self.boundaries[1]

        # kill the mol, effectively resetting it
        self.simulation.runCommand(f'killmol {name}')

        # redistribute the molecule according to the bounds
        self.simulation.addSolutionMolecules(
            name,
            config['molecules'].get(name)['count'],
            highpos=high_bounds,
            lowpos=low_bounds
        )

    def schema(self) -> Dict:
        """Return a dictionary of molecule names and the expected input/output schema at simulation
            runtime. NOTE: Smoldyn assumes a global high and low bounds and thus high and low
            are specified alongside molecules.
        """
        tuple_type = {'_type': 'tuple', '_apply': 'set'}
        list_type = {'_type': 'list', '_apply': 'set'}
        return {
            'molecules': {
                mol_name: {
                    'coordinates': tuple_type,
                    'velocity': tuple_type,  # QUESTION: could the expected shape be: ((0,0), (1,4)) where: ((xStart, xStop), (yStart, yStop)) ie directional?
                    #'mol_type': 'string',
                    'count': 'int',
                    'state': 'string'
                } for mol_name in self.species_names
            },
            'high': list_type,
            'low': list_type
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

        # get the molecule configs
        molecules = state['molecules']

        # distribute the mols according to self.boundaries
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

    molecules_config = {
        'red': {
            'coordinates': (0,0),
            'velocity': (0,0),
            'mol_type': 'red',
            'count': 250,
            'state': 'soln'
        },
        'green': {
            'coordinates': (1,0),
            'velocity': (0,0),
            'mol_type': 'green',
            'count': 5,
            'state': 'soln'
        }
    }

    # this is the instance for the composite process to run
    instance = {
        'smoldyn': {
            '_type': 'process',
            'address': 'local:smoldyn_process',
            'config': {
                'model_filepath': 'smoldyn_process/examples/model_files/crowding_model.txt',
                'animate': False,
                #'molecules': molecules_config,
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
