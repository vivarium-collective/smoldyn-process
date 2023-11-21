"""
Smoldyn Process
"""


from typing import *
import numpy as np
import smoldyn as sm
from process_bigraph import Process, Step, Composite, process_registry, types
from smoldyn_process.sed2 import pf
from smoldyn_process.utils import SmoldynModel


class SmoldynProcess(Step):
    config_schema = {
        'model_filepath': 'string',
    }

    def __init__(self, config: Union[Dict, None] = None):
        super().__init__(config)

        # initialize the simulator from a Smoldyn model.txt file.
        if not self.config.get('model_filepath'):
            raise ValueError('The config requires a path to a Smoldyn model file.')

        # create an instance of SmoldynModel
        model = SmoldynModel(self.config.get('model_filepath'))

        #self.simulator: sm.Simulation = sm.Simulation.fromFile(self.config['model_filepath'])
        self.simulator: sm.Simulation = model.simulation

        # get input ports as above
        # self.input_ports = list(model.counts.keys())

        self.input_ports = [
            'species',
            'model_parameters'
        ]

        # in the case of this particular model file, listmols is output and thus species should be counted.
        self.output_ports = [
            'species'
        ]

        # Get the species
        self.species_list = [self.simulator.getSpeciesName(i) for i in range(model.counts.get('species'))]

        # Get boundaries for uniform
        self.boundaries = self.simulator.getBoundaries()

        # Get model parameters
        self.model_parameters_dict = model.definitions

        # Get a list of reactions
        self.reaction_list = model.query('reaction')


    # TODO -- is initial state even working for steps?
    def initial_state(self, config: Union[Dict, None] = None):
        """NOTE: Due to the nature of this model, Smoldyn assigns a random uniform distribution of
            integers as the initial coordinate (x, y, z) values for the simulation.

            Args:
                config:`Dict`: configuration by which to read the relevant values at initialization
                    of simulation. Defaults to `None`.
        """
        # create species dict of coordinates and initialize to None
        species_dict = {}
        for spec in self.species_list:
            species_dict[spec] = None

        # create boundaries dict, accounting for each agent:
        n_boundaries = len(self.boundaries) - 1
        boundaries_dict = {
            'low': [self.boundaries[n_boundaries - 1] for spec in self.species_list],
            'high': [self.boundaries[n_boundaries] for spec in self.species_list]
        }

        return {
            'time': 0.0,
            'species': species_dict,
            'boundaries': boundaries_dict,
            'model_parameters': self.model_parameters_dict
        }

    def schema(self):
        return {
            'inputs': {
                'time': 'float',
                'time_stop': 'float',
                'dt': 'float'
            },
            'outputs': {
                'results': {'_type': 'numpy_array', '_apply': 'set'}  # TODO: update Smoldyn-specific return type
            }
        }

    def update(self, inputs):
        results = self.simulator.run(inputs['time_stop'], inputs['dt'])
        return {
            'results': results
        }


class TelluriumProcess(Process):
    config_schema = {
        'model_filepath': 'string',
        'record_history': 'bool',  # TODO -- do we have this type?
    }

    def __init__(self, config=None):
        super().__init__(config)

        # initialize a tellurium(roadrunner) simulation object. Load the model in using either sbml(default) or antimony
        if self.config.get('antimony_string') and not self.config.get('sbml_model_path'):
            self.simulator = te.loada(self.config['antimony_string'])
        elif self.config.get('sbml_model_path') and not self.config.get('antimony_string'):
            self.simulator = te.loadSBMLModel(self.config['sbml_model_path'])
        else:
            raise Exception('the config requires either an "antimony_string" or an "sbml_model_path"')

        # TODO -- make this configurable.
        self.input_ports = [
            'floating_species',
            'boundary_species',
            'model_parameters'
            # 'time',
            # 'compartments',
            # 'parameters',
            # 'stoichiometries',
        ]

        self.output_ports = [
            'floating_species',
            # 'time',
        ]

        # Get the species (floating and boundary)
        self.floating_species_list = self.simulator.getFloatingSpeciesIds()
        self.boundary_species_list = self.simulator.getBoundarySpeciesIds()
        self.floating_species_initial = self.simulator.getFloatingSpeciesConcentrations()
        self.boundary_species_initial = self.simulator.getBoundarySpeciesConcentrations()

        # Get the list of parameters and their values
        self.model_parameters_list = self.simulator.getGlobalParameterIds()
        self.model_parameter_values = self.simulator.getGlobalParameterValues()

        # Get a list of reactions
        self.reaction_list = self.simulator.getReactionIds()

    def initial_state(self, config=None):
        floating_species_dict = dict(zip(self.floating_species_list, self.floating_species_initial))
        boundary_species_dict = dict(zip(self.boundary_species_list, self.boundary_species_initial))
        model_parameters_dict = dict(zip(self.model_parameters_list, self.model_parameter_values))
        return {
            'time': 0.0,
            'floating_species': floating_species_dict,
            'boundary_species': boundary_species_dict,
            'model_parameters': model_parameters_dict
        }

    def schema(self):
        float_set = {'_type': 'float', '_apply': 'set'}
        return {
            'time': 'float',
            'floating_species': {
                species_id: float_set for species_id in self.floating_species_list},
            'boundary_species': {
                species_id: float_set for species_id in self.boundary_species_list},
            'model_parameters': {
                param_id: float_set for param_id in self.model_parameters_list},
            'reactions': {
                reaction_id: float_set for reaction_id in self.reaction_list},
        }

    def update(self, state, interval):

        # set tellurium values according to what is passed in states
        for port_id, values in state.items():
            if port_id in self.input_ports:  # only update from input ports
                for cat_id, value in values.items():
                    self.simulator.setValue(cat_id, value)

        # run the simulation
        new_time = self.simulator.oneStep(state['time'], interval)

        # extract the results and convert to update
        update = {'time': new_time}
        for port_id, values in state.items():
            if port_id in self.output_ports:
                update[port_id] = {}
                for cat_id in values.keys():
                    update[port_id][cat_id] = self.simulator.getValue(cat_id)
        return update



process_registry.register('tellurium_step', TelluriumStep)
process_registry.register('tellurium_process', TelluriumProcess)


def test_process():

    # this is the instance for the composite process to run
    instance = {
        'tellurium': {
            '_type': 'process',
            'address': 'local:tellurium_process',  # using a local toy process
            'config': {
                'sbml_model_path': 'demo_processes/BIOMD0000000061_url.xml',
            },
            'wires': {
                'time': ['time_store'],
                'floating_species': ['floating_species_store'],
                'boundary_species': ['boundary_species_store'],
                'model_parameters': ['model_parameters_store'],
                'reactions': ['reactions_store'],
            }
        },
        'emitter': {
            '_type': 'step',
            'address': 'local:ram-emitter',
            'config': {
                'ports': {
                    'inputs': {
                        'floating_species': 'tree[float]'
                    }
                }
            },
            'wires': {
                'inputs': {
                    'floating_species': ['floating_species_store'],
                }
            }
        }
    }

    # make the composite
    workflow = Composite({
        'state': instance
    })

    # initial_state = workflow.initial_state()

    # run
    workflow.run(10)

    # gather results
    results = workflow.gather_results()
    print(f'RESULTS: {pf(results)}')


def test_step():

    # this is the instance for the composite process to run
    instance = {
        'start_time_store': 0,
        'run_time_store': 1,
        'results_store': None,  # TODO -- why is this not automatically added into the schema because of tellurium schema?
        'tellurium': {
            '_type': 'step',
            'address': 'local:tellurium_step',  # using a local toy process
            'config': {
                'sbml_model_path': 'demo_processes/BIOMD0000000061_url.xml',
            },
            'wires': {
                'inputs': {
                    'time': ['start_time_store'],
                    'run_time': ['run_time_store'],
                    'floating_species': ['floating_species_store'],
                    'boundary_species': ['boundary_species_store'],
                    'model_parameters': ['model_parameters_store'],
                    'reactions': ['reactions_store'],
                },
                'outputs': {
                    'results': ['results_store'],
                }
            }
        }
    }

    # make the composite
    workflow = Composite({
        'state': instance
    })

    # initial_state = workflow.initial_state()

    # run
    update = workflow.run(10)

    print(f'UPDATE: {update}')

    # gather results
    # results = workflow.gather_results()
    # print(f'RESULTS: {pf(results)}')



if __name__ == '__main__':
    # test_process()
    test_step()

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
            'X': 10
        }
    }

    # run the simulation
    sim_settings = {
        'total_time': 100,
        'initial_state': initial_state
    }
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

    import ipdb;
    ipdb.set_trace()


if __name__ == '__main__':
    # test_smoldyn_process()
    test_load_file()
