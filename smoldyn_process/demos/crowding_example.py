"""The output data returned by that which is required by simularium (executiontime, listmols),
    when written and read into the same file is as follows:

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
from smoldyn_process.processes.smoldyn_process import SmoldynProcess


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
