from smoldyn_process.sed2.builder import Builder, Node
import json
class SEDBuilder(Builder):
    def __init__(self, ontologies, tree=None):
        super().__init__(tree)
        self['ontologies'] = ontologies
        self['models'] = Node()
        self['simulators'] = Node()
        self['tasks'] = Node()

    def add_model(self, model_id, source):
        self["models"][model_id] = {
            "id": model_id,
            "source": source
        }

    def add_simulator(self, simulator_id, type):
        self["simulators"][simulator_id] = {
            "id": simulator_id,
            "_type": type
        }

    def to_json(self, filename):
        with open(f'{filename}.json', 'w') as file:
            json.dump(self.tree, file, indent=4)


def test_builder():
    # Initialize the SEDBuilder
    demo_workflow = SEDBuilder(ontologies=['KISAO', 'sbml', 'biomodels'])

    # Add a model
    demo_workflow.add_model('example_model', 'path/to/model/file')

    # Add a simulator
    demo_workflow.add_simulator('example_simulator', 'KISAO:example_algorithm')

    # Create a task and add a simulation to it
    demo_workflow.add_task('example_simulation_task', inputs=[], outputs=[])

    # Define simulation parameters
    start_time = 0
    end_time = 100
    number_of_points = 1000
    demo_workflow[ 'example_simulation_task'].add_simulation(
        'example_simulation',
        simulator_id='example_simulator',
        model_id='example_model',
        start_time=start_time,
        end_time=end_time,
        number_of_points=number_of_points,
        observables=[]  # Define observables as needed
    )
    demo_workflow.to_json('sed2demo1')

    demo_workflow



    # 2
    demo_workflow = SEDBuilder(ontologies=['KISAO', 'sbml', 'biomodels'])
    demo_workflow.add_model('model1', 'biomodels:BIOMD0000000246')
    demo_workflow.add_simulator('simulator1', 'KISAO:CVODE')


    demo_workflow.add_task(
        'initial_simulations',
        inputs=[],
        outputs=[])

    demo_workflow['initial_simulations'].add_simulation(
        'sim1',
        simulator_id='simulator1',
                                                                      model_id='model1',
        start_time=0,
        end_time=100,
                                                                      number_of_points=1000,
                                                                      observables=['observable1', 'observable2'])

    demo_workflow.to_json('sed2demo2')



if __name__ == '__main__':
    test_builder()
