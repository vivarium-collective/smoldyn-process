"""
Builder
=======
"""

import pprint

pretty = pprint.PrettyPrinter(indent=2)


def pf(x):
    return pretty.pformat(x)


class Node(dict):
    def add_process(
            self,
            process_id,
            process_type=None,
            address=None,
            config=None,
            inputs=None,
            outputs=None,
    ):
        self[process_id] = {
            '_type': process_type or 'process',
            'address': address or '',
            'config': config or {},
            'wires': {
                'inputs': inputs or {},
                'outputs': outputs or {},
            },
        }
        return self

    def add_task(
            self,
            task_id,
            inputs=None,
            outputs=None
    ):
        self[task_id] = Node({
            '_type': 'task',
            'inputs': inputs or {},
            'outputs': outputs or {},
        })
        return self[task_id]  # Return the new task node

    def add_simulation(
            self,
            simulation_id,
            simulator_id=None,
            model_id=None,
            start_time=None,
            end_time=None,
            number_of_points=None,
            observables=None
    ):
        self[simulation_id] = Node({
            '_type': 'simulation',
            'config': {
                'simulator_id': simulator_id,
                'model_id': model_id,
                'start_time': start_time,
                'end_time': end_time,
                'number_of_points': number_of_points,
                'observables': observables
            }
        })
        return self[simulation_id]  # Return the new simulation node

class Builder(Node):

    def __init__(self, tree=None):
        super().__init__()
        self.tree = tree or {}

    def __setitem__(self, keys, value):
        # Convert single key to tuple
        keys = (keys,) if isinstance(keys, str) else keys

        # Navigate through the keys, creating nested dictionaries as needed
        d = self.tree
        for key in keys[:-1]:  # iterate over keys to create the nested structure
            if key not in d:
                d[key] = Node()
            d = d[key]
        d[keys[-1]] = value  # set the value at the final level

    def __getitem__(self, keys):
        # Convert single key to tuple
        keys = (keys,) if isinstance(keys, str) else keys

        d = self.tree
        for key in keys:
            d = d[key]  # move deeper into the dictionary
        return d

    def __repr__(self):
        return f"{pf(self.tree[self.top_path])}"



def test_builder():
    # Testing the Builder class
    b = Builder()
    b['path', 'to', 'node'] = 1.0
    print(b.tree)

    # Accessing the value
    value = b['path', 'to', 'node']
    print(value)

    b['path', 'b2', 'c'] = 12.0
    print(b)

    b.add_process(process_id='process1')
    b['path', 'to'].add_process(process_id='p1', process_type='example_type')
    print(b['path'])


    # print(b.state)  # this should be the state hierarchy
    print(b.processes)  # This should be the process registry
    # print(b['path', 'b2', 'c'].type)  # access schema keys
    #
    # b['path', 'to', 'p1'].connect(port_id='', target=['path', '1'])  # connect port, with checking
    #
    # b.check()  # check if everything is connected
    # b.infer()  # fill in missing content
    # b.graph()  # bigraph-viz



def test_builder_demo():

    sed_schema = {
        'models': {},
        'algorithms': {},
        'visualizations': {},
        'tasks': {},
    }
    a = Builder(sed_schema)

    # or
    b = Builder()
    b['models'] = {}
    b['algorithms'] = {}
    b['visualizations'] = {}
    b['tasks'] = {}

    b.add_process(process_id='p1', address='', config={}, inputs={}, outputs={})


    b





if __name__ == '__main__':
    # test_builder()
    test_builder_demo()
