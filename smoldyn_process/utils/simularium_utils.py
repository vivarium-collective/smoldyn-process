from typing import *
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


def add_plot_to_trajectory(converter: TrajectoryConverter, plot_function, **plot_settings) -> None:
    plot = plot_function(**plot_settings)
    return converter.add_plot(plot)


def scatter_plot(
        title: str,
        xaxis_title: str,
        yaxis_title: str,
        xtrace: np.ndarray,
        ytraces: Dict[str, np.ndarray],
        render_mode: str
        ) -> ScatterPlotData:
    return ScatterPlotData(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        xtrace=xtrace,
        ytraces=ytraces,
        render_mode=render_mode
    )


def histogram(
        title: str,
        xaxis_title: str,
        traces: Dict[str, Any]
        ) -> HistogramPlotData:
    return HistogramPlotData(
        title=title,
        xaxis_title=xaxis_title,
        traces=traces
    )


def generate_simularium_file_from_trajectory(converter: TrajectoryConverter, file_save_name: str) -> None:
    return converter.save(file_save_name)


def generate_new_simularium_file(**params):
    """Generate a new simularium file for a simulation.

        Kwargs:
            params = {
                'simulation_data': {
                    molecule_ids: List[str],
                    molecule_coordinates: List[List[float]],
                    total_steps: int,
                    timestep: float,
                    file_save_name: str,
                    box_size: int = 100,
                },
                'plot_config': {
                    'total_time': interval (from update()),
                    'counts:': {
                        spec_id: spec_count,
                        for spec_id in self.species_names
                    },
                },
                'file_name': simularium save fp
            }

    """
    trajectory = generate_simularium_trajectory(**params['simulation_data'])
    converter = generate_trajectory_converter(trajectory)
    plot_config = {
        'title': 'species counts',
        'xaxis_title': 'time',
        'yaxis_title': 'counts',
        'xtrace': np.array(list(range(params['plot_config']['total_time']))),
        'ytraces': {
            **params['plot_config']['counts']
        },
        'render_mode': 'lines'
    }
    add_plot_to_trajectory(converter, scatter_plot, **plot_config)
    return generate_simularium_file_from_trajectory(converter, params['file_name'])



