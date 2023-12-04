"""The output data returned by that which is required by simularium (executiontime, listmols),
    when written and read into the same file for a given global time is as follows:

    [identity, state, x, y, z, serial number], where:

        identity = species identity for molecule
        state = state of the given molecule
        x, y, z = values for the relative coordinates
        serial_number = monotonically decreasing timestamp for the given species_id

        At each global timestep (`executiontime`), a new 'cast of characters' are introduced that may resemble the
            cast of characters at the first timestep, but are in fact different and thus all the molecules provided
            from the `listmols` command will in fact all be unique.


    I propose the following consideration at each `update` step:

    The `smoldyn.Simulation().connect()` method can be used to (for example) tell the
    simulation about external environmental parameters that change over the course of
    the simulation. For example:

        a = None
        avals = []

        def new_difc(t, args):
            global a, avals
            x, y = args
            avals.append((t, a.difc['soln']))
            return x * math.sin(t) + y

        def update_difc(val):
            global a
            a.difc = val

        def test_connect():
            global a, avals
            sim = smoldyn.Simulation(low=(.......
            a = sim.addSpecies('a', color=black, difc=0.1)

            # specify either function as target:
            sim.connect(new_dif, update_difc, step=10, args=[1,1])

            # ...or species as target:
            sim.connect(func = new_dif, target = ’a.difc’, step=10, args=[0, 1])

            sim.run(....


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

        The current implementation of this class assumes 3 key conditions:
            1. that a smoldyn model file is present and working
            2. that output commands are not listed in the Smoldyn
                model file. If they are, simply comment them out before using this.
            3. that no actual parameter values are passed in the `config_schema`, but rather a path to a smoldyn
                model file. TODO: Expand this statement.

    # TODO: Figure this out:
    To start, we have:
        - modelfile

    We can also either:
        - keep output commands in modelfile to get output file
        - pass the model output file along with the model file

    ...for the purpose of telling the process what output to expect?

    """

    # TODO: Add the ability to pass model parameters and not just a model file.
    config_schema = {
        'model_filepath': 'string',
        'animate': 'bool',
    }

    def __init__(self, config: Dict = None):
        """A new instance of `SmoldynProcess` based on the `config` that is passed. The schema for the config to be passed in
            this object's constructor is as follows:

            config_schema = {
                'model_filepath': 'string',  <-- analogous to python `str`
                'animate': 'bool'  <-- of type `bigraph_schema.base_types.bool`


            # TODO: It would be nice to have classes associated with this.
        """
        super().__init__(config)

        # specify the model fp for clarity
        self.model_filepath = self.config.get('model_filepath')

        # enforce model filepath passing
        if not self.model_filepath:
            raise ValueError(
                '''
                    The Process configuration requires a Smoldyn model filepath to be passed.
                    Please specify a 'model_filepath' in your instance configuration.
                '''
            )

        # initialize the simulator from a Smoldyn model.txt file.
        self.simulation: sm.Simulation = sm.Simulation.fromFile(self.model_filepath)

        # get a list of the simulation species
        species_count = self.simulation.count()['species']
        self.species_names: List[str] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            if 'empty' not in species_name.lower():
                self.species_names.append(species_name)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step...
        self.boundaries: Dict[str, List[float]] = dict(zip(['low', 'high'], self.simulation.getBoundaries()))

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl_better')

        # make molecule counts dataset
        self.simulation.addOutputData('species_counts')
        # write molcounts to counts dataset at every timestep (shape=(n_timesteps, 1+n_species <-- one for time)): [timestep, countSpec1, countSpec2, ...]
        self.simulation.addCommand(cmd='molcount species_counts', cmd_type='E')

        # make molecules dataset (molecule information)
        self.simulation.addOutputData('molecules')
        # write coords to dataset at every timestep (shape=(n_output_molecules, 7)): seven being [timestep, smol_id(species), mol_state, x, y, z, mol_serial_num]
        self.simulation.addCommand(cmd='listmols molecules', cmd_type='E')

        # set molecule ids to none, as they are not available until after the simulation runs
        self.molecule_ids: List[str] = []

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
        initial_conditions = {
            mol_name: {
                'count': self.simulation.getMoleculeCount(mol_name, MolecState.all),
                'coordinates': [0.0 for _ in range(6)]
            } for mol_name in self.species_names
        }

        # place uniform and then getOUtputData

        # TODO: fill these with a default state with get initial mol state method
        state = {
            'molecules': initial_conditions
        }
        return state

    def set_uniform(self, name: str, config: Dict[str, Any], kill_mol: bool = True) -> None:
        """Add a distribution of molecules to the solution in
            the simulation memory given a higher and lower bound x,y coordinate. Smoldyn assumes
            a global boundary versus individual species boundaries. Kills the molecule before dist if true.
            TODO: If pymunk expands the species compartment, account for
            expanding `highpos` and `lowpos`. This method should be used within the body/logic of
            the `update` class method.

            Args:
                name:`str`: name of the given molecule.
                config:`Dict`: molecule state.
                kill_mol:`bool`: kills the molecule based on the `name` argument, which effectively
                    removes the molecule from simulation memory.
        """
        # kill the mol, effectively resetting it
        if kill_mol:
            self.simulation.runCommand(f'killmol {name}')

        # redistribute the molecule according to the bounds
        self.simulation.addSolutionMolecules(
            name,
            config['count'],
            highpos=config['high'],
            lowpos=config['low']
        )

    def schema(self) -> Dict:
        """Return a dictionary of molecule names and the expected input/output schema at simulation
            runtime. NOTE: Smoldyn assumes a global high and low bounds and thus high and low
            are specified alongside molecules.

            PLEASE NOTE: the key 'counts' refers to the count of molecules for each molecular species. The number of
                species_types in this regard does not change, even if that number drops to 0.
        """

        # TODO: Include listmols3 spec for spec in self.species_names
        counts_type = {
            species_name: 'float'
            for species_name in self.species_names
        }

        molecules_type = {
            mol_id: {
                'coordinates': 'list[float]',
                'species_id': 'string'
            } for mol_id in self.molecule_ids
        }
        """
        { 
            'species_counts': {
                spec_id: int
            }

            'molecules': {
               molId--> molid from listmols2[-1] aka serial number : {
                  coords: list[float] --> listmols2[3:5]
                  species_id: string (red or green)--> species id from listmols2[1]
        """
        # TODO: include velocity and state to this schema (add to constructor as well)
        return {
            'species_counts': counts_type,
            'molecules': molecules_type
        }

    def update(self, state: Dict, interval: int) -> Dict:
        """Callback method to be evoked at each Process interval. We want to get the
            last of each dataset type as that is the relevant data in regard to the Process timescale scope.

            Args:
                state:`Dict`: current state of the Smoldyn simulation, expressed as a `Dict` whose
                    schema matches that which is returned by the `self.schema()` API method.
                interval:`int`: Analogous to Smoldyn's `time_stop`, this is the
                    timestep interval at which to provide the update as the output of this method.
                    NOTE: This update is iteratively called with the `Process` API.

            Returns:
                `Dict`: New state according to the update at interval


            TODO: We must account for the mol_ids that are generated in the output based on the interval run,
                i.e: Shorter intervals will yield both less output molecules and less unique molecule ids.
        """
        # reset the molecules, distribute the mols according to self.boundaries
        for mol_name, mol_state in state['molecules'].items():  # change term here
            self.set_uniform(mol_name, {
                'count': mol_state['count'],
                'high': self.boundaries['high'],
                'low': self.boundaries['low']
            })

        # run the simulation for a given interval
        self.simulation.run(
            stop=interval,
            dt=self.simulation.dt
        )

        # get the counts data, clear the buffer
        counts_data = self.simulation.getOutputData('species_counts')

        # get the data based on the commands added in the constructor, clear the buffer
        molecules_data = self.simulation.getOutputData('molecules')

        # update the list of known molecule ids
        for molecule in molecules_data:
            self.molecule_ids.append(str(molecule[1]))

        # get the final counts for the update
        final_count = counts_data[-1]

        # remove the timestep from the list
        final_count.pop(0)

        simulation_state = {
            'species_counts': {},
            'molecules': {}
        }
        for index, name in enumerate(self.species_names):
            simulation_state['species_counts'][name] = {
                name: int(final_count[index]) - state['species_counts'][name]
            }
            '''molecules[name] = {
                'count': int(final_count[index]) - state['species_counts'][name],
                'coordinates': final_location
            }'''

        # TODO -- post processing to get effective rates

        return {'molecules': molecules}


# register the process above as the name passed in the first argument below
process_registry.register('smoldyn', SmoldynProcess)


def test_process():
    """Test the smoldyn process using the crowding model."""

    # this is the instance for the composite process to run
    instance = {
        'smoldyn': {
            '_type': 'process',
            'address': 'local:smoldyn',
            'config': {
                'model_filepath': 'smoldyn_process/models/model_files/crowding_model.txt',
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
                        'molecules': 'tree[string]'
                    },
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
