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


def get_model_as_list(model_fp: str) -> List[str]:
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


def get_value_from_model_list(model_fp: str, value: str) -> List[Tuple[str]]:
    model_as_list = get_model_as_list(model_fp)
    values = []
    for line in model_as_list:
        if line.startswith(value):
            values.append(tuple(line.split()))
    return values


class SmoldynModel:
    def __init__(self, fp: str):
        self.fp = fp
        self.model_list = self._model_as_list()
        # self.definitions = self._modeL_definitions()

    def _model_as_list(self) -> List[str]:
        """Get a Smoldyn model file in the form of a list of strings delimited by line break.

            Returns:
                `List[str]` : model file as list
        """
        sim_spec = validate_model(self.fp)
        for item in sim_spec:
            if isinstance(item, tuple):
                for member in item:
                    if isinstance(member, list):
                        return member

    def _modeL_definitions(self) -> List[Tuple[str]]:
        return self.get_value('define')

    def get_value(self, value: str) -> List[Tuple[str]]:
        values = []
        for line in self.model_list:
            if line.startswith(value):
                values.append(tuple(line.split()))
            else:
                raise ValueError(f'{value} is not a searchable parameter.')
        return values
