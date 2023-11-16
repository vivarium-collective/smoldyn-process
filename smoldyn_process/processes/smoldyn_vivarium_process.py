"""
=======
Smoldyn
=======

Execute by running: ``python smoldyn_process/processes/smoldyn_vivarium_process.py``
"""

import os

import smoldyn as sm
from process_bigraph import Process, Step, Composite, process_registry, types


class Smoldyn(Process):
    """ Smoldyn Process

    A spatial stochastic simulator for chemical reaction networks

    http://www.smoldyn.org/index.html

    TODO: suppress print out
    TODO: configure surfaces
    """

    defaults = {
        'animate': False,
        'time_step': 10,
        'low': [0, 0],
        'high': [10, 10],
        'boundary': 'p',
        'dt': 0.1,
        'species': {},
        'reactions': {},
        # TODO: add parameters for defining compartments and surfaces
        'file': None,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        self.dt = self.parameters['dt']

        # initialize the simulation
        if self.parameters['file']:
            self.simulation = sm.Simulation.fromFile(self.parameters['file'], "q")
        else:
            self.simulation = sm.Simulation(
                low=self.parameters['low'],
                high=self.parameters['high'],
                types=self.parameters['boundary'],
                setFlags="q"
            )

        # set output type
        self.simulation.addOutputData('counts')
        self.simulation.addCommand(cmd='molcount counts', cmd_type='E')

        # get the species names
        species_count = self.simulation.count()['species']
        self.species = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            self.species.append(species_name)

        # make the species
        species = {}
        for name, config in self.parameters['species'].items():
            species[name] = self.simulation.addSpecies(name, **config)
            self.species.append(name)

        # make the reactions
        for rxn_name, config in self.parameters['reactions'].items():
            substrate_names = config.pop('subs')
            product_names = config.pop('prds')
            substrates = [species[name] for name in substrate_names]
            products = [species[name] for name in product_names]
            self.simulation.addReaction(
                rxn_name,
                subs=substrates,
                prds=products,
                **config)

        if self.parameters['animate']:
            self.simulation.addGraphics('opengl')

    # TODO: make this work with compartments
    def set_compartment(self, name, config):
        self.simulation.runCommand(f'killmol {name}')
        self.simulation.addCompartmentMolecules(
            config.get('compartment'),
            name,
            config.get('counts'),
            highpos=config.get('high'),
            lowpos=config.get('low'))

    # TODO: provide another function for adding surfaces
    # def set_surface(.......) ?

    def set_uniform(self, name, config):
        self.simulation.runCommand(f'killmol {name}')
        self.simulation.addSolutionMolecules(
            name,
            config.get('counts'),
            highpos=config.get('high'),
            lowpos=config.get('low'))

    def ports_schema(self):
        return {
            # TODO -- molecules have counts OR locations. make this optional
            'molecules': {
                mol_id: {
                    '_default': 0,
                    '_updater': 'accumulate',
                    '_emit': True,
                } for mol_id in self.species
            }
        }

    def next_update(
            self,
            timestep,
            states
    ):

        # reset the molecules, at a uniform distribution
        for name, counts in states['molecules'].items():
            self.set_uniform(name, {
                'counts': counts,
                'high': self.parameters['high'],
                'low': self.parameters['low']})

        # run simulation
        self.simulation.run(
            stop=timestep,
            dt=self.dt)

        # get the data, clear the buffer
        data = self.simulation.getOutputData('counts', True)

        # get the final counts for the update
        final_counts = data[-1]
        molecules = {}
        for index, name in enumerate(self.parameters['species'].keys(), 1):
            molecules[name] = int(final_counts[index]) - states['molecules'][name]

        # TODO -- post processing to get effective rates

        return {
            'molecules': molecules,
            # 'effective_rates': {},
        }


# functions to configure and run the process
def test_smoldyn_process(
        animate=False
):
    # initialize the process by passing in parameters
    parameters = {
        'animate': animate,
        'species': {
            'X': {'difc': 0},
            'A': {'difc': 1},
            'B': {'difc': 1},
            'A2': {'difc': 1},
            'B2': {'difc': 1}},
        'reactions': {
            'express': {
                'subs': ['X'],
                'prds': [
                    'X', 'A', 'B'],
                'rate': 1},
            'Adimer': {
                'subs': ['A', 'A'],
                'prds': ['A2'],
                'rate': 1},
            'Adimer_reverse': {
                'subs': ['A2'],
                'prds': ['A', 'A'],
                'rate': 1},
            'Bdimer': {
                'subs': ['B', 'B'],
                'prds': ['B2'],
                'rate': 1},
            'Bdimer_reverse': {
                'subs': ['B2'],
                'prds': ['B', 'B'],
                'rate': 1},
            'AxB': {
                'subs': ['A2', 'B'],
                'prds': ['A2'],
                'rate': 1},
            'Adegrade': {
                'subs': ['A'],
                'prds': [],
                'rate': 1},
            'Bdegrade': {
                'subs': ['B'],
                'prds': [],
                'rate': 1}}}

    process = Smoldyn(parameters)

    # declare the initial state
    initial_state = {
        'molecules': {
            'X': 10}}

    # run the simulation
    sim_settings = {
        'total_time': 100,
        'initial_state': initial_state}
    output = simulate_process(
        process,
        sim_settings)

    return output


def test_load_file():
    parameters = {
        'file': 'smoldyn_process/examples/template.txt'
    }
    smoldyn = Smoldyn(parameters)
    
    # declare the initial state
    initial_state = {
        'molecules': {
            'E': 10,
            'S': 1000}}

    # run the simulation
    sim_settings = {
        'total_time': 100,
        'initial_state': initial_state}

    output = simulate_process(
        smoldyn,
        sim_settings)

    import ipdb; ipdb.set_trace()



if __name__ == '__main__':
    # test_smoldyn_process()
    test_load_file()
