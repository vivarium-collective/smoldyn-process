'''simulation experiment design demos

The composition schema was developed for integrative simulations, but can also be used for workflows such as simulation
experiments. This experimental notebook demonstrates simulation experiments as composites, going from the declarative
JSON format to executable python script.

Example scripts were provided here: https://docs.google.com/document/d/1jZkaNhM_cOqMWtd4sJZ9b0VGXPTLsDKsRNI5Yvu4nOA/edit
'''

from process_bigraph import Composite


def test_sed1():
    instance = {
        'start_time_store': 0,
        'run_time_store': 10,
        'curves_store': [
            {'x': 'time', 'y': '[GlcX]'},
            {'x': 'time', 'y': '[Glc]'}
        ],
        'figure_store': {'_type': 'string'},
        'uniform_time_course': {
            '_type': 'step',
            'address': 'local:tellurium_step',
            'config': {
                'sbml_model_path': 'demo_processes/BIOMD0000000061_url.xml',
            },
            'wires': {
                'inputs': {
                    'time': ['start_time_store'],
                    'run_time': ['run_time_store'],
                },
                'outputs': {
                    'results': ['results_store'],
                }
            }
        },
        'plot2d': {
            '_type': 'step',
            'address': 'local:plot2d',
            'config': {
                'filename': 'figure1'
            },
            'wires': {
                'inputs': {
                    'results': ['results_store'],
                    'curves': ['curves_store'],
                },
                'outputs': {
                    'figure_path': ['figure_store']
                }
            }
        }
    }

    workflow = Composite({
        'state': instance
    })

    fig = workflow.state['figure_store']
    print(f'FIGURE: {fig}')


def test_sed19():
    # Run multiple stochastic simulations, compute means and standard deviations.
    instance = {
        'summary_statistics': {
            '_type': 'step',
            'address': '',
            'config': {
                'report': ['mean', 'standard_deviation'],
                'n_sims': 10,
            },
            'wires': {
                'simulation': ['sim'],
                'results': ['results_store'],
            },
            'sim': {
                '_type': 'step',
                'address': 'local:tellurium_step',
                'config': {
                    'sbml_model_path': 'demo_processes/BIOMD0000000061_url.xml',
                },
                'wires': {
                    'inputs': {
                        'time': ['start_time_store'],
                        'run_time': ['run_time_store'],
                    },
                    'outputs': {
                        'results': ['results_store'],
                    }
                }
            },
        }
    }

    workflow = Composite({
        'state': instance
    })

    workflow.run()


def test_sed21():
    # Run a simulation, change the structure of the model, rerun the simulation, compare.
    instance = {
        'run_ensembles': {
            '_type': 'step',
            'address': '',
            'config': {},
            'sim': {
                '_type': 'step',
                'address': 'local:tellurium_step',
                'config': {
                    'sbml_model_path': 'demo_processes/BIOMD0000000061_url.xml',
                },
                'wires': {
                    'inputs': {
                        'time': ['start_time_store'],
                        'run_time': ['run_time_store'],
                    },
                    'outputs': {
                        'results': ['results_store'],
                    }
                }
            },
            'wires': {
                'simulation': ['sim']
            },
        },
        'compare_results': {
            '_type': 'step',
        }
    }

    workflow = Composite({
        'state': instance
    })

    workflow.run()



if __name__ == '__main__':
    test_sed1()
    test_sed19()
