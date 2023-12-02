"""The output data returned by that which is required by simularium (executiontime, listmols),
    when written and read into the same file for a given global time is as follows:

    [identity, state, x, y, z, serial number], where:

        identity = species identity for molecule
        state = state of the given molecule
        x, y, z = values for the relative coordinates
        serial_number = monotonically decreasing timestamp for the given species_id


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
            if 'empty' not in species_name.lower():
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
        """
        list_type = {
            species_name: {
                '_type': 'float',
                '_apply': 'set',
            }
            for species_name in self.species_names
        }
        """
        { 
            'species_counts': {
                id: int
            }

            'particles': {
               molId : {
                  coords: list[float]
                  species: string (red or green)
        """
        return {
            'molecules': {
                mol_name: {
                    'count': 'int',  # derived from the molcount output command
                    'coordinates': 'list[float]',
                    # 'velocity': tuple_type,  # QUESTION: could the expected shape be: ((0,0), (1,4)) where: ((xStart, xStop), (yStart, yStop)) ie directional?
                    'mol_type': 'string',
                    # 'state': 'string'
                } for mol_name in self.species_names
            },
            # 'global_time': 'float'
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
        counts_data = self.simulation.getOutputData('molecule_counts', True)

        # get the data based on the commands added in the constructor, clear the buffer
        location_data = self.simulation.getOutputData('molecule_locations', True)

        # get the final counts for the update
        final_count = counts_data[-1]
        final_location = location_data[-1]
        molecules = {}
        for index, name in enumerate(self.species_names, 1):
            molecules[name] = {
                'count': int(final_count[index]) - state['molecules'][name],
                'coordinates': final_location
            }

        # TODO -- post processing to get effective rates

        return {'molecules': molecules}


# register the process above as the name passed in the first argument below
process_registry.register('smoldyn', SmoldynProcess)
