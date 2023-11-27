"""
SED2 builder

demos are according to this:
    - https://docs.google.com/document/d/1jZkaNhM_cOqMWtd4sJZ9b0VGXPTLsDKsRNI5Yvu4nOA/edit
"""
from sed2.old.sedbuilder import SEDBuilder

MODEL_PATH = 'demos/Caravagna2010.xml'


def test_builder():
    # Example usage:
    sed = SEDBuilder()

    # Load an SBML model
    sed.add_model(
        name='model1',
        type='sbml',
        source='demos/BIOMD0000000061_url.xml',  # TODO -- this should move the file into an archive
    )

    # Set up the simulator
    sed.add_simulator(
        name='simulator1',
        simulator='tellurium',
        version='',
        kisao_id='0000029',  # Gillespie direct algorithm
    )

    # make the first step
    sed.add_task(task_id='1')

    # add a simulation
    sed['1'].add_simulation(
        simulation_id='sim1',
        simulator_id='simulator1',
        model_id='model1',
    )


def test_sed1():


    # Initialize the SEDBuilder with some ontologies
    demo_workflow = SEDBuilder(ontologies=['KISAO', 'sbml', 'biomodels'])

    # Load an SBML model
    demo_workflow.add_model(
        model_id='model1',
        source='biomodels:BIOMD0000000246',
    )

    # Set up the simulator
    demo_workflow.add_simulator(
        simulator_id='simulator1',
        type='KISAO:CVODE',
    )

    # Create two tasks
    demo_workflow.add_task(task_id='initial_simulation', inputs=[], outputs=[])
    demo_workflow.add_task(task_id='modify_model', inputs=[], outputs=[])

    # Task 1
    ## Add the first simulation
    demo_workflow['initial_simulation'].add_simulation(
        simulation_id='initial_run', simulator_id='simulator1', model_id='model1',
        start_time=0, end_time=100, number_of_points=1000,
        outputs=['observable1', 'observable2'],
    )

    # Task 2
    ## change model
    demo_workflow.add_model(model_id='model2', source='model1', changes={'param1': 2.0})

    ## run second simulation
    demo_workflow['modify_model'].add_simulation(
        simulation_id='second_run', simulator_id='simulator1', model_id='model2',
        start_time=0, end_time=100, number_of_points=1000,
        outputs=['observable1', 'observable2'],
    )

    # verify
    demo_workflow.verify()

    # save
    demo_workflow.to_json(filename='sed2demo')
    demo_workflow.to_archive()



if __name__ == '__main__':
    # test_builder()
    test_sed1()
