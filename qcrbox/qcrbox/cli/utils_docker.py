import pathlib
import re
from pathlib import Path
from typing import TypeVar

import yaml


PathLike = TypeVar("PathLike", str, pathlib.Path)


def get_all_services(compose_file: PathLike):
    docker_compose_data = yaml.safe_load(Path(compose_file).open())
    return list(docker_compose_data["services"].keys())


def get_build_dependencies(service: str, compose_file: PathLike):
    """
    Return list of qcrbox docker images that are build dependencies for `service`.

    These are obtained by looking for lines in `service`'s Dockerfile starting
    with `FROM qcrbox/<some_docker_image>`
    """
    docker_compose_path = Path(compose_file)
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


def get_runtime_dependencies(service: str, compose_file: PathLike):
    """
    Return list of qcrbox docker services that are runtime dependencies for `service`.

    These are obtained from the `depends_on` key in the given `docker_compose_file`.
    """
    docker_compose_path = Path(compose_file)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    try:
        runtime_deps = docker_compose_data["services"][service]["depends_on"]
    except KeyError:
        # no runtime dependencies
        runtime_deps = []

    if isinstance(runtime_deps, dict):
        runtime_deps = list(runtime_deps.keys())

    return runtime_deps


def get_build_and_runtime_dependencies(service_name, compose_file):
    return get_build_dependencies(service_name, compose_file) + get_runtime_dependencies(service_name, compose_file)


def tidy_up_deps(deps_done, deps_todo):
    return list({x: None for x in deps_todo if x not in deps_done}.keys())


def get_dependency_chain(service_name, compose_file):
    deps_done = []
    deps_todo = [service_name]

    while deps_todo != []:
        cur_dep = deps_todo.pop(0)
        deps_done.append(cur_dep)
        deps_todo += get_build_and_runtime_dependencies(cur_dep, compose_file)
        deps_todo = tidy_up_deps(deps_done, deps_todo)

    deps_without_input_service = list(reversed(deps_done))[:-1]
    return deps_without_input_service
