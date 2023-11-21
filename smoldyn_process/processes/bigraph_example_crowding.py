"""
Smoldyn Process using the model found at `../examples/model_files/crowding_model.txt`
"""


from typing import *
import numpy as np
import smoldyn as sm
from process_bigraph import Process, Step, Composite, process_registry, types
from smoldyn_process.sed2 import pf
from smoldyn_process.utils import query_model, model_definitions


class SmoldynProcess(Step):
    """Smoldyn bi-graph process."""

    config_schema = {
        'model_filepath': 'string',
    }

    '''def __init__(self, config: Union[Dict, None] = None):
        super().__init__(config)

        # ensure correct config parameters
        if not self.config.get('model_filepath'):
            raise ValueError('The config requires a path to a Smoldyn model file.')

        # create an instance of SmoldynModel
        # TODO: Would it be helpful to create a generic Model object since everything is from file in the API?
        model = SmoldynModel(self.config['model_filepath'])

        # initialize the simulator from a Smoldyn model.txt file.
        self.simulation: sm.Simulation = model.simulation
        # self.simulator: sm.Simulation = sm.Simulation.fromFile(self.config['model_filepath']) ???

        # get input ports as above
        self.input_ports: List[str] = ['species', 'model_parameters']
        # self.input_ports = list(model.counts.keys()) ???

        # in the case of this particular model file, listmols is output and thus species should be counted.
        self.output_ports = [
            'species'
        ]

        # Get the species
        self.species_list: List[str] = [
            self.simulation.getSpeciesName(i) for i in range(model.counts.get('species'))
        ]

        # Get boundaries for uniform
        self.boundaries: Tuple[List[float], List[float]] = self.simulation.getBoundaries()

        # Get model parameters
        self.model_parameters_dict: Dict[str, int] = model.definitions
        self.model_parameters_list: List[str] = list(self.model_parameters_dict.keys())

        # Get a list of reactions
        self.reaction_list: List[Tuple[str]] = model.query('reaction', stringify=True)'''

    def __init__(self, config=None):
        super().__init__(config)
        if not self.config.get('model_filepath'):
            raise ValueError('The config requires a path to a Smoldyn model file.')

        # TODO: Would it be helpful to create a generic Model object since everything is from file in the API?

        # initialize the simulator from a Smoldyn model.txt file.
        self.simulator: sm.Simulation = sm.Simulation.fromFile(self.config['model_filepath'])





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

    '''def schema(self):
        return {
            'inputs': {
                'time': 'float',
                'time_stop': 'float',
                'dt': 'float'
            },
            'outputs': {
                'results': {'_type': 'numpy_array', '_apply': 'set'}  # TODO: update Smoldyn-specific return type
            }
        }'''

    def schema(self):
        float_set = {'_type': 'float', '_apply': 'set'}
        string_set = float_set = {'_type': 'string', '_apply': 'set'}
        return {
            'time': 'float',
            'species': {
                species_id: float_set for species_id in self.species_list
            },
            'boundaries': {
                species_id: float_set for species_id in self.boundaries
            },
            'model_parameters': {
                param_id: float_set for param_id in self.model_parameters_list
            },
            'reactions': {
                reaction_id: string_set for reaction_id in self.reaction_list
            },
        }

    '''def update(self, inputs):
        results = self.simulator.run(inputs['time_stop'], inputs['dt'])
        return {
            'results': results
        }'''

    def update(self, state, interval):
        # HERE IS WHERE Simulation.updateSim() should go!!!!!
        # set tellurium values according to what is passed in states
        for port_id, values in state.items():
            if port_id in self.input_ports:  # only update from input ports
                for cat_id, value in values.items():
                    self.simulation.setValue(cat_id, value)

        # run the simulation
        new_time = self.simulation.oneStep(state['time'], interval)

        # extract the results and convert to update
        update = {'time': new_time}
        for port_id, values in state.items():
            if port_id in self.output_ports:
                update[port_id] = {}
                for cat_id in values.keys():
                    update[port_id][cat_id] = self.simulation.getValue(cat_id)
        return update


# register the smoldyn process
process_registry.register('smoldyn_process', SmoldynProcess)


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
