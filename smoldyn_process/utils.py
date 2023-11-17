import os
from typing import *
import smoldyn as sm


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

