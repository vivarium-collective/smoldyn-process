import os
from typing import *
from abc import ABC, abstractmethod
import pandas as pd
import smoldyn as sm
import numpy as np
from simulariumio import (
    TrajectoryConverter,
    TrajectoryData,
    AgentData,
    UnitData,
    MetaData,
    ScatterPlotData,
    HistogramPlotData,
    DisplayData,
    ModelMetaData,
    CameraData,
    DISPLAY_TYPE
)
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
    if sim_spec[0] or sim_spec[1]:
        raise Exception('There were errors in the Smoldyn model file that could not be validated.')
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


def model_definitions(model_fp: str) -> Dict[str, float]:
    """Return a dict following the Smoldyn standard for model definition nomenclature, i.e\n:
        `define NAME VALUE`. These model definitions effectively act as constants and coefficients for the
        given model simulation.

        Args:
            model_fp:`str`: path to the Smoldyn model being queried.

        Returns:
            `Dict[str, float]`
    """
    definitions = {}
    defs = query_model(model_fp, 'define')
    for definition in defs:
        if not len(definition) >= 3:
            raise AttributeError(f'the definition: {definition} is improperly formatted.')
        name = definition[1]
        value = definition[2]
        definitions[name] = float(value)
    return definitions


def get_reactions(model_fp: str):
    """This expects to output a dict of:

    {reaction name: {
        'subs': [a list of reaction substrates],
        'prds': [a list of reaction products corresponding to each sub],
        }
    }
    """

    _reactions = {}
    reactions = query_model(model_fp, 'reaction')
    for reaction in reactions:
        reaction_spec = {'subs': [], 'prds': []}
        reaction_name = reaction[0]
        if not 'reaction_probability' in reaction:
            split_reaction = reaction.split(' -> ')
            subs = split_reaction[0]
            prds = split_reaction[1]
            reaction_spec['subs'].append(subs)
            reaction_spec['prds'].append(prds)
            _reactions[reaction_name] = reaction_spec
    return _reactions


def create_listmols_dataframe(model_fp: str = None, values: List[List[float]] = None) -> pd.DataFrame:
    """TODO: Add simulation read -> output spec -> run -> getData functionality."""
    cols = ['species_id', 'state', 'x', 'y', 'z', 'serial_number']
    return pd.DataFrame(data=values, columns=cols)


def read_model_file_as_list(fp: str) -> List[str]:
    """Return either a Smoldyn configuration(input) or Smoldyn output model file as a list of strings.

        Args:
            fp:`str`: filepath to the configuration or output file.

        Returns:
            The file contents as a list of strings delimited by new line breaks.
    """
    with open(fp, 'r') as file:
        lines = file.readlines()
    return [line.rstrip('\n') for line in lines]


def get_output_molecule_ids(output_fp: str, unique: bool = True) -> List[str]:
    """Return all output molecule ids(names) from a specified Smoldyn output file generated from the Smoldyn `listmols`
        command. If `unique` is set to `True`, the output molecule names will be returned as a set of unique
        molecule names only as a list, otherwise a list of all molecule names.

        Args:
            output_fp:`str`: filepath to the Smoldyn output file generated from the `listmols` command. PLEASE NOTE:
                this function will raise an Exception if the output file was generated from any other command, as
                the contents is expected to be particularly formatted.
            unique:`bool`: If set to `True`, returns a set of only unique names, otherwise all names. Defaults
                to `True`.

        Returns:
            All output molecule names resulting from the simulation.
    """
    output_contents = read_model_file_as_list(output_fp)
    molecule_ids = [line.split()[0] for line in output_contents]
    return list(set(molecule_ids)) if unique else molecule_ids


class ProcessModel(ABC):
    """An Abstract class that is meant to be more generalized than just Smoldyn."""
    fp: str
    reactions: List
    definitions: Dict

    def __init__(self, fp: str):
        self.fp = fp

    @abstractmethod
    def reactions(self):
        pass

    @abstractmethod
    def definitions(self):
        pass

    @abstractmethod
    def query(self, term):
        pass

    @abstractmethod
    def get_species(self):
        pass


def generate_simularium_trajectory(
        molecule_ids: List[str],
        molecule_coordinates: List[List[float]],
        total_steps: int,
        timestep: float,
        file_save_name: str,
        box_size: int = 100,
) -> TrajectoryData:
    n_agents = len(molecule_ids)
    type_names = []
    for t in range(total_steps):
        type_names.append([mol_id for mol_id in molecule_ids])

    all_radii = []
    for t in range(total_steps):
        all_radii.append([0.01 for n in molecule_ids])

    all_display_data = {
        mol_id: DisplayData(
            name=mol_id,
            display_type=DISPLAY_TYPE.SPHERE,
        ) for mol_id in molecule_ids
    }

    return TrajectoryData(
        meta_data=MetaData(
            box_size=np.array([box_size, box_size, box_size]),
            camera_defaults=CameraData(
                position=np.array([10.0, 0.0, 200.0]),
                look_at_position=np.array([10.0, 0.0, 0.0]),
                fov_degrees=60.0,
            ),
            trajectory_title="Smoldyn Process",
            model_meta_data=ModelMetaData(
                title="Some agent-based model",
                version="8.1",
                authors="A Modeler",
                description=(
                    "An agent-based model run with some parameter set"
                ),
                doi="10.1016/j.bpj.2016.02.002",
                source_code_url="https://github.com/simularium/simulariumio",
                source_code_license_url="https://github.com/simularium/simulariumio/blob/main/LICENSE",
                input_data_url="https://allencell.org/path/to/native/engine/input/files",
                raw_output_data_url="https://allencell.org/path/to/native/engine/output/files",
            ),
        ),
        agent_data=AgentData(
            times=timestep * np.array(list(range(total_steps))),
            n_agents=np.array(total_steps * [n_agents]),
            viz_types=np.array(total_steps * [n_agents * [1000.0]]),  # default viz type = 1000
            unique_ids=np.array(total_steps * [list(range(n_agents))]),
            types=type_names,
            positions=np.array(molecule_coordinates),
            radii=all_radii,
            display_data=all_display_data
        ),
        time_units=UnitData("ns"),  # nanoseconds
        spatial_units=UnitData("nm"),  # nanometers
    )


def generate_trajectory_converter(trajectory: TrajectoryData) -> TrajectoryConverter:
    return TrajectoryConverter(trajectory)


def add_plot_to_trajectory(converter: TrajectoryConverter, plot_function, **plot_settings):
    plot = plot_function(**plot_settings)
    return converter.add_plot(plot)


def scatter_plot(
        title: str,
        xaxis_title: str,
        yaxis_title: str,
        xtrace: np.ndarray,
        ytraces: Dict[str, np.ndarray],
        render_mode: str
        ):
    return ScatterPlotData(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        xtrace=xtrace,
        ytraces=ytraces,
        render_mode=render_mode
    )


def generate_simularium_file_from_trajectory(converter: TrajectoryConverter, file_save_name: str) -> None:
    return converter.save(file_save_name)
