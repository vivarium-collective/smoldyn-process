"""
Smoldyn Process using the model found at `../examples/model_files/crowding_model.txt`
"""


from typing import *
import numpy as np
import smoldyn as sm
from process_bigraph import Process, Composite, process_registry, types
from smoldyn_process.sed2 import pf
from smoldyn_process.utils import query_model, model_definitions, list_model


class SmoldynProcess(Process):
    """Smoldyn-based implementation of bi-graph process' `Process` API."""

    config_schema = {
        'model_filepath': 'string',
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

        # query the model file to ensure that the appropriate Smoldyn output commands are present
        if not query_model(self.model_filepath, 'cmd'):
            self.simulation.addOutputData('executiontime')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 executiontime', cmd_type='i')
            self.simulation.addOutputData('listmols')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 listmols', cmd_type='i')

        # get a list of the reactions
        self.reactions: List[str] = query_model(self.model_filepath, 'reaction', stringify=True)

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
            self.simulation.addGraphics('opengl')

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

    def set_uniform(self, name, config):
        self.simulation.runCommand(f'killmol {name}')
        self.simulation.addSolutionMolecules(
            name,
            config.get('counts'),
            highpos=config.get('high'),
            lowpos=config.get('low'))

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
