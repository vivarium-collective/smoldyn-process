"""The output data returned by that which is required by simularium (executiontime, listmols),
    when written and read into the same file is as follows:

    [global_timestep, species_id, x, y, z, local_timestep], where:

        global_timestep = global timestamp which will be equivalent to n in range(time_stop) which
            increases according to dt
        species_id = unique species id (based on simulation.count()['species'] value
        x, y, z = values for the relative coordinates
        local_timestep = monotonically decreasing timestamp for the given species_id


"""


from typing import *
import numpy as np
import smoldyn as sm
from smoldyn._smoldyn import MolecState
from process_bigraph import Process, Composite, process_registry, types
from smoldyn_process.sed2 import pf


class SmoldynProcess(Process):
    """Smoldyn-based implementation of bi-graph process' `Process` API. Please note the following:

    For the purpose of this `Process` implementation,

    at each `update`, we need the function to do the following for each molecule/species in the simulation:

        - Get the molecule count with Smoldyn lang: (`molcount {molecule_name}`) shape: [time, ...speciesN],
            so in the case of a two species simulation: [timestamp, specACounts, specBCounts]
        - Get the molecule positions and relative corresponding time steps,
            indexed by the molecule name with Smoldyn lang: (`listmols`)[molecule_name]
        - ?Get the molecule state?
        - Kill the molecule with smoldyn lang: (`killmol {molecule_name}`)
        - Add the molecule back to the solution(cytoplasm), effectively resetting it at boundary coordinates with Python API: (`simulation.addMolecules()

    PLEASE NOTE:

        The current implementation of this class assumes 2 key conditions:
            1. that a smoldyn model file is present and working
            2. that output commands are not listed in the Smoldyn
                model file. If they are, simply comment them out before using this.

    """

    config_schema = {
        'model_filepath': 'string',
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

        # get a list of the simulation species
        species_count = self.simulation.count()['species']
        self.species_names: List[str] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            self.species_names.append(species_name)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step...
        self.boundaries: Dict[str, List[float]] = dict(zip(['low', 'high'], self.simulation.getBoundaries()))

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl_better')

        # add the relevant output datasets and commands required for the update
        # make time dataset
        self.simulation.addOutputData('time')
        # write executiontime to time dataset at every timestep
        self.simulation.addCommand(cmd='executiontime time', cmd_type='E')

        # make molecule counts dataset
        self.simulation.addOutputData('molecule_counts')
        # write molcount header to counts dataset at start of simulation
        self.simulation.addCommand(cmd='molcountheader molecule_counts', cmd_type='B')
        # write molcounts to counts dataset at every timestep
        self.simulation.addCommand(cmd='molcount molecule_counts', cmd_type='E')

        # make coordinates dataset
        self.simulation.addOutputData('molecule_locations')
        # write coords to dataset at every timestep
        self.simulation.addCommand(cmd='listmols molecule_locations', cmd_type='E')

    def initial_state(self) -> Dict[str, Dict]:
        """Set the initial parameter state of the simulation. This method should return an implementation of
            that which is returned by `self.schema()`.


        NOTE: Due to the nature of this model,
            Smoldyn assigns a random uniform distribution of integers as the initial coordinate (x, y, z)
            values for the simulation. As such, the `set_uniform` method will uniformly distribute
            the molecules according to a `highpos`[x,y] and `lowpos`[x,y] where high and low pos are
            the higher and lower bounds of the molecule spatial distribution.

            NOTE: This method should provide an implementation of the structure denoted in `self.schema`.
        """

        # TODO: update for distribution!
        initial_conditions = {}

        for name in self.species_names:
            count = self.simulation.getMoleculeCount(name, MolecState.all)
            initial_conditions[name] = {
                'time': 0,
                'count': count,
                'coordinates': [],
            }

        # TODO: fill these with a default state with get initial mol state method
        state = {
            'molecules': initial_conditions
        }
        return state

    def set_uniform(self, name: str, config: Dict[str, Any]) -> None:
        """Add a distribution of molecules to the solution in
            the simulation memory given a higher and lower bound x,y coordinate. Smoldyn assumes
            a global boundary versus individual species boundaries.
            TODO: If pymunk expands the species compartment, account for
            expanding `highpos` and `lowpos`. This method should be used within the body/logic of
            the initial state and update class methods.

            Args:
                name:`str`: name of the given molecule.
                config:`Dict`: molecule state.
        """
        # kill the mol, effectively resetting it
        self.simulation.runCommand(f'killmol {name}')

        # redistribute the molecule according to the bounds
        self.simulation.addSolutionMolecules(
            name,
            config['molecules'].get(name)['count'],
            highpos=self.boundaries['high'],
            lowpos=self.boundaries['low']
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
                    'time': 'int',
                    'count': 'int',  # derived from the molcount output command
                    'coordinates': list_type,
                    # 'velocity': tuple_type,  # QUESTION: could the expected shape be: ((0,0), (1,4)) where: ((xStart, xStop), (yStart, yStop)) ie directional?
                    # 'mol_type': 'string',
                    # 'state': 'string'
                } for mol_name in self.species_names
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

        # get the time data, clear the buffer
        time_data = self.simulation.getOutputData('time', True)

        # get the counts data, clear the buffer
        counts_data = self.simulation.getOutputData('molecule_counts', True)

        # get the data based on the commands added in the constructor, clear the buffer
        location_data = self.simulation.getOutputData('molecule_locations', True)

        # get the final counts for the update
        final_time = time_data[-1]
        final_counts = counts_data[-1]
        final_locations = location_data[-1]
        molecules = {}
        for index, name in enumerate(self.species_names, 1):
            molecules[name] = {
                'time': final_time,
                'count': int(final_counts[index]) - state['molecules'][name],
                'coordinates': final_locations
            }

        # uniformly reset the solution molecules based on the updated count for each molecule
        for species_name in self.species_names:
            spec_config = state['molecules'].get(species_name)
            self.set_uniform(species_name, spec_config)

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
                'model_filepath': 'smoldyn_process/examples/model_files/crowding_model.txt',
                'animate': False,
            },
            'wires': {  # this should return that which is in the schema
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
