import pathlib
import re
from pathlib import Path
from typing import TypeVar

import yaml


PathLike = TypeVar("PathLike", str, pathlib.Path)


def get_all_services(docker_compose_file: PathLike):
    docker_compose_path = Path(docker_compose_file)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    return list(docker_compose_data["services"].keys())


def get_build_dependencies(service: str, docker_compose_file: PathLike):
    """
    Return list of qcrbox docker images that are build dependencies for `service`.

    These are obtained by looking for lines in `service`'s Dockerfile starting
    with `FROM qcrbox/<some_docker_image>`
    """
    docker_compose_path = Path(docker_compose_file)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    root_dir = docker_compose_path.parent
    dockerfile = root_dir.joinpath(docker_compose_data["services"][service]["build"]["context"]).joinpath(
        "Dockerfile"
    )
    contents = dockerfile.open().readlines()
    dependency_lines = [line for line in contents if line.startswith("FROM qcrbox")]
    dependency_names = [
        re.match("^FROM qcrbox/(?P<image_name>.*):", line).group("image_name") for line in dependency_lines
    ]
    return dependency_names


def get_runtime_dependencies(service: str, docker_compose_file: PathLike):
    """
    Return list of qcrbox docker services that are runtime dependencies for `service`.

    These are obtained from the `depends_on` key in the given `docker_compose_file`.
    """
    docker_compose_path = Path(docker_compose_file)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    try:
        runtime_deps = docker_compose_data["services"][service]["depends_on"]
    except KeyError:
        # no runtime dependencies
        runtime_deps = []

    if isinstance(runtime_deps, dict):
        runtime_deps = list(runtime_deps.keys())

    return runtime_deps
