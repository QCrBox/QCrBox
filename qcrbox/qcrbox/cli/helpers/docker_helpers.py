import os
import pathlib
import re
import subprocess
import sys

from git import Repo
from loguru import logger
from pathlib import Path
from typing import TypeVar

import yaml

__all__ = ["build_single_docker_image", "get_dependency_chain"]

# Type alias
PathLike = TypeVar("PathLike", str, pathlib.Path)

DOCKER_COMPOSE_PROJECT_NAME = "qcrbox"


def get_repo_root():
    repo = Repo(".", search_parent_directories=True)
    return Path(repo.working_tree_dir)


def get_toplevel_docker_compose_path():
    return get_repo_root().joinpath("docker-compose.dev.yml")


def get_toplevel_env_file_path():
    return get_repo_root().joinpath(".env.dev").as_posix()


def get_docker_compose_args(compose_file: Path):
    return [
        f"--project-name={DOCKER_COMPOSE_PROJECT_NAME}",
        f"--env-file={get_toplevel_env_file_path()}",
        f"--file={compose_file.as_posix()}",
    ]


def run_docker_compose_command(cmd: str, *args, compose_file: Path):
    docker_compose_args = get_docker_compose_args(compose_file)
    all_args = docker_compose_args + [cmd] + list(args)
    # all_kwargs = kwargs.copy()
    # all_kwargs.update(dict(_in=sys.stdin, _out=sys.stdout, _err=sys.stderr))
    # logger.info(f"Running docker compose build with args={all_args}, kwargs={all_kwargs}")
    logger.info(f"Running docker compose {cmd} with args={all_args}")
    cmd = ["docker", "compose", *docker_compose_args, cmd, *args]
    # logger.info(f"Subprocess cmd={cmd}")
    proc = subprocess.run(cmd, shell=False, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, env=os.environ)
    proc.check_returncode()


def get_all_services(compose_file: PathLike):
    docker_compose_data = yaml.safe_load(Path(compose_file).open())
    return list(docker_compose_data["services"].keys())


def get_build_dependencies(service: str, compose_file: Path):
    """
    Return list of qcrbox docker images that are build dependencies for `service`.

    These are obtained by looking for lines in `service`'s Dockerfile starting
    with `FROM qcrbox/<some_docker_image>`
    """
    docker_compose_data = yaml.safe_load(Path(compose_file).open())
    root_dir = compose_file.parent
    dockerfile = root_dir.joinpath(docker_compose_data["services"][service]["build"]["context"]).joinpath("Dockerfile")
    contents = dockerfile.open().readlines()
    dependency_lines = [line for line in contents if line.startswith("FROM qcrbox")]
    dependency_names = [
        re.match("^FROM qcrbox/(?P<image_name>.*):", line).group("image_name") for line in dependency_lines
    ]
    return dependency_names


def get_runtime_dependencies(service: str, compose_file: Path):
    """
    Return list of qcrbox docker services that are runtime dependencies for `service`.

    These are obtained from the `depends_on` key in the given `docker_compose_file`.
    """
    docker_compose_data = yaml.safe_load(compose_file.open())
    try:
        runtime_deps = docker_compose_data["services"][service]["depends_on"]
    except KeyError:
        # no runtime dependencies
        runtime_deps = []

    if isinstance(runtime_deps, dict):
        runtime_deps = list(runtime_deps.keys())

    return runtime_deps


def get_build_and_runtime_dependencies(service_name: str, compose_file: Path):
    return get_build_dependencies(service_name, compose_file) + get_runtime_dependencies(service_name, compose_file)


def tidy_up_deps(deps_done, deps_todo):
    return list({x: None for x in deps_todo if x not in deps_done}.keys())


def get_dependency_chain(service_name, compose_file: PathLike):
    compose_file = Path(compose_file)

    deps_done = []
    deps_todo = [service_name]

    while deps_todo != []:
        cur_dep = deps_todo.pop(0)
        deps_done.append(cur_dep)
        deps_todo += get_build_and_runtime_dependencies(cur_dep, compose_file)
        deps_todo = tidy_up_deps(deps_done, deps_todo)

    deps_without_input_service = list(reversed(deps_done))[:-1]
    return deps_without_input_service


def build_single_docker_image(target_image: str, compose_file: PathLike, dry_run: bool):
    logger.debug(f"Building docker image: {target_image}")
    if not dry_run:
        run_docker_compose_command("build", target_image, compose_file=Path(compose_file))


def start_up_docker_containers(target_containers: list[str], compose_file: PathLike, dry_run):
    logger.debug(f"Starting up docker container(s): {', '.join(target_containers)}")
    if not dry_run:
        run_docker_compose_command("up", "-d", *target_containers, compose_file=Path(compose_file))


def spin_down_docker_containers(compose_file: PathLike):
    logger.debug(f"Stop and remove QCrBox docker containers")
    run_docker_compose_command("down", compose_file=Path(compose_file))
