import os
from typing import *
import smoldyn as sm
from biosimulators_simularium.converters.utils import validate_model


def get_smoldyn_model_from_file(model_fp: str) -> sm.Simulation:
    return sm.Simulation.fromFile(model_fp)


def get_counts_from_file(model_fp: str) -> Dict:
    return get_smoldyn_model_from_file(model_fp).count()


def get_species(sim: sm.Simulation) -> List[str]:
    """Read the species names from the given Smoldyn model file.

        Args:
            sim:`smoldyn.Simulation`: simulation from file

        Returns:
            `List[str]`: A list of smoldyn simulation species.
    """
    species = []
    for i in range(sim.count().get('species')):
        s = sim.getSpeciesName(i)
        species.append(s)
    return species


def get_species_from_model_file(model_fp: str) -> List[str]:
    """Get a list of species names originating from a smoldyn model file.

        Args:
            model_fp:`str`: filepath belonging to the given smoldyn model.

        Returns:
            `List[str]`: species names
    """
    sim = get_smoldyn_model_from_file(model_fp)
    return get_species(sim)


def list_model(model_fp: str) -> List[str]:
    """Get a Smoldyn model file in the form of a list of strings delimited by line break.

        Args:
            model_fp:`str`

        Returns:
            `List[str]` : model file as list
    """
    sim_spec = validate_model(model_fp)
    for item in sim_spec:
        if isinstance(item, tuple):
            for member in item:
                if isinstance(member, list):
                    return member


def query_model(model_fp: str, value: str, stringify: bool = False) -> Union[List[Tuple[str]], List[str]]:
    """Query `self.model_list` for a given value/set of values and return
        a list of single-space delimited tuples of queried values. Raises a `ValueError`
        if the value is not found as a term at the model in `model_fp`.

            TODO: filter out comments and replace any definitions with the actual value.

            Args:
                model_fp:`str`: path belonging to the queried model.
                value:`str`: value by which to query the document.
                stringify:`bool`: if set to `True`, returns the query results as single strings rather than
                    delimited tuples. Defaults to `False`.

            Returns:
                `Union[List[Tuple[str]], List[str]]`
    """

    def _query_model(model_fp: str, value: str) -> List[Tuple[str]]:
        model_as_list = list_model(model_fp)
        values = []
        for line in model_as_list:
            if line.startswith(value):
                values.append(tuple(line.split()))
        if not values:
            raise ValueError(f'{value} was not found in the model file.')
        else:
            return values

    result_list = _query_model(model_fp, value)
    if stringify:
        stringified_results = []
        for result in result_list:
            r = " ".join(result)
            stringified_results.append(r)
        return stringified_results
    else:
        return result_list


def model_definitions(model_fp: str):
    pass


class SmoldynModel:
    def __init__(self, fp: str):
        self.fp = fp
        self.validation = self._validate_model()
        self.definitions = self._model_definitions()
        self.simulation = self._simulation()
        self.counts = self._counts()
        self.dt = self._dt()

    def _validate_model(self):
        return validate_model(self.fp)

    def _model_definitions(self) -> Dict[str, float]:
        """Return a dict following the Smoldyn standard for model definition nomenclature, i.e\n:
            `define NAME VALUE`.
        """
        definitions = {}
        defs = self._query('define')
        for definition in defs:
            if not len(definition) >= 3:
                raise AttributeError(f'the definition: {definition} is improperly formatted.')
            name = definition[1]
            value = definition[2]
            definitions[name] = float(value)
        return definitions

    def _simulation(self):
        for item in self.validation:
            if isinstance(item, tuple):
                for member in item:
                    if isinstance(member, sm.Simulation):
                        return member

    def _counts(self):
        return self.simulation.count()

    def _dt(self):
        return self.simulation.dt

    def _query(self, value: str) -> List[Tuple[str]]:
        values = []
        for line in self.list_model():
            if line.startswith(value):
                values.append(tuple(line.split()))
        if not values:
            raise ValueError(f'{value} was not found in the model file.')
        else:
            return values

    def query(self, value: str, stringify: bool = False) -> Union[List[Tuple[str]], List[str]]:
        """Query `self.model_list` for a given value/set of values and return
            a list of single-space delimited tuples of queried values. Raises a `ValueError`
            if the value is not found as a term in `self.list_model`.

            TODO: filter out comments and replace any definitions with the actual value.

            Args:
                value:`str`: value by which to query the document.
                stringify:`bool`: if set to `True`, returns the query results as single strings rather than
                    delimited tuples. Defaults to `False`.

            Returns:
                `Union[List[Tuple[str]], List[str]]`
        """
        result_list = self._query(value)
        if stringify:
            stringified_results = []
            for result in result_list:
                r = " ".join(result)
                stringified_results.append(r)
            return stringified_results
        else:
            return result_list

    def list_model(self) -> List[str]:
        """Get a Smoldyn model file in the form of a list of strings delimited by line break.

            Returns:
                `List[str]` : model file as list
        """
        for item in self.validation:
            if isinstance(item, tuple):
                for member in item:
                    if isinstance(member, list):
                        return member

    def execute_simulation(self):
        return self.simulation.run(self.simulation.stop, self.simulation.dt)

