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

        '''# query the model file to ensure that the appropriate Smoldyn output commands are present
        if not query_model(self.model_filepath, 'cmd'):
            self.simulation.addOutputData('executiontime')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 executiontime', cmd_type='i')
            self.simulation.addOutputData('listmols')
            self.simulation.addCommand(cmd=f'0 {self.simulation.stop} 2 listmols', cmd_type='i')

        # TODO: Will this work?
        # Add counts to outputs
        self.simulation.addOutputData('counts')
        self.simulation.addCommand(cmd='molcount counts', cmd_type='E')'''

        # get a list of the reactions
        self.reactions: List[str] = query_model(self.model_filepath, 'reaction', stringify=True)

        # get the species names
        species_count = self.simulation.count()['species']
        self.species: List[str] = []
        for index in range(species_count):
            species_name = self.simulation.getSpeciesName(index)
            self.species.append(species_name)

        # make the species
        species = {}
        for name, config in self.config['species'].items():
            species[name] = self.simulation.addSpecies(name, **config)
            self.species.append(name)

        # make the reactions
        """
        Below expects the reaction to be in the form of a dict where:
            reaction = {
                'subs': substrate values/ids,
                'prds': product values/ids,
        """
        for rxn_name, config in self.reactions.items():
            substrate_names = config.pop('subs')
            product_names = config.pop('prds')
            substrates = [species[name] for name in substrate_names]
            products = [species[name] for name in product_names]
            self.simulation.addReaction(
                rxn_name,
                subs=substrates,
                prds=products,
                **config)

        # get the simulation boundaries, which in the case of Smoldyn denote the physical boundaries
        # TODO: add a verification method to ensure that the boundaries do not change on the next step
        self.boundaries = self.simulation.getBoundaries()

        # set graphics (defaults to False)
        if self.config['animate']:
            self.simulation.addGraphics('opengl')

    def initial_state(self):
        """NOTE: Due to the nature of this model, Smoldyn assigns a random uniform distribution of
            integers as the initial coordinate (x, y, z) values for the simulation.


            Args:
                config:`Dict`: configuration by which to read the relevant values at initialization
                    of simulation. Defaults to `None`.
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
                    'velocity': tuple_type,
                    'mol_type': {'_type': 'string', '_apply': 'set'},
                    'counts': 'int'
                } for mol_name in self.species
            }
        }

    def update(self, state, interval):
        ##UPDATE FOR SMOLDYN!
        # set reaction bounds
        reaction_bounds = state['reaction_bounds']
        for reaction_id, bounds in reaction_bounds.items():
            self.model.reactions.get_by_id(reaction_id).bounds = (bounds['lower_bound'], bounds['upper_bound'])

        # run solver
        solution = self.model.optimize()

        return {
            'fluxes': solution.fluxes.to_dict(),
            'objective_value': solution.objective_value
        }


# register the smoldyn process
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
