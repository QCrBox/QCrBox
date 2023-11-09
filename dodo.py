import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

import yaml
from loguru import logger
from doit.tools import LongRunning


DOIT_CONFIG = {
    "default_tasks": ["show_usage"],
    "verbosity": 2,
    "backend": "sqlite3",
}

DOCKER_COMPOSE_FILE = "docker-compose.dev.yml"

DOCKER_COMPOSE_ARGS = [
    "--project-name=qcrbox",
    "--env-file=.env.dev",
    f"--file={DOCKER_COMPOSE_FILE}",
]


def run_docker_compose_command(cmd, *args):
    all_args = DOCKER_COMPOSE_ARGS + [cmd] + list(args)
    logger.info(f"Running docker compose build with args={all_args}")
    cmd = ["docker", "compose", *DOCKER_COMPOSE_ARGS, cmd, *args]
    subprocess.run(cmd, shell=False, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, env=os.environ)


def task_docs_build():
    """
    Build the documentation
    """
    return {
        "basename": "docs-build",
        "actions": ["mkdocs build"],
    }


def task_docs_serve():
    """
    Serve the documentation using the local development server and open it in a web browser.
    """

    def open_url(url):
        webbrowser.open(url, new=2)

    return {
        "basename": "docs-serve",
        "actions": [
            (open_url, ["http://127.0.0.1:8000/"]),
            LongRunning("mkdocs serve"),
        ],
    }


def get_build_dependencies(service_name, docker_compose_file=None):
    docker_compose_path = Path(docker_compose_file or DOCKER_COMPOSE_FILE)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    root_dir = docker_compose_path.parent
    dockerfile = root_dir.joinpath(docker_compose_data["services"][service_name]["build"]["context"]).joinpath(
        "Dockerfile"
    )
    contents = dockerfile.open().readlines()
    dependency_lines = [line for line in contents if line.startswith("FROM qcrbox")]
    dependency_names = [
        re.match("^FROM qcrbox/(?P<image_name>.*):", line).group("image_name") for line in dependency_lines
    ]
    return dependency_names


def get_runtime_dependencies(service_name, docker_compose_file=None):
    docker_compose_path = Path(docker_compose_file or DOCKER_COMPOSE_FILE)
    docker_compose_data = yaml.safe_load(docker_compose_path.open())
    try:
        runtime_deps = docker_compose_data["services"][service_name]["depends_on"]
    except KeyError:
        # no runtime dependencies
        runtime_deps = []

    if isinstance(runtime_deps, dict):
        runtime_deps = list(runtime_deps.keys())

    return runtime_deps


def get_build_and_runtime_dependencies(service_name):
    return get_build_dependencies(service_name) + get_runtime_dependencies(service_name)


def tidy_up_deps(deps_done, deps_todo):
    return list({x: None for x in deps_todo if x not in deps_done}.keys())


def get_dependency_chain(service_name):
    deps_done = []
    deps_todo = [service_name]

    while deps_todo:
        cur_dep = deps_todo.pop(0)
        deps_done.append(cur_dep)
        deps_todo += get_build_and_runtime_dependencies(cur_dep)
        deps_todo = tidy_up_deps(deps_done, deps_todo)

    return reversed(deps_done)


def build_single_docker_image(target_image):
    logger.debug(f"Building docker image: {target_image}")
    run_docker_compose_command("build", target_image)


def build_incl_dependencies(target_images):
    for target_image in target_images:
        for service_name in get_dependency_chain(target_image):
            build_single_docker_image(service_name)


def build_docker_images(target_images, no_deps=False):
    if no_deps:
        run_docker_compose_command("build", *target_images)
    else:
        build_incl_dependencies(target_images)


def task_build():
    """
    Build docker images.
    """
    return {
        "actions": [build_docker_images],
        "pos_arg": "target_images",
        "params": [
            {
                "name": "no_deps",
                "long": "no-deps",
                "type": bool,
                "default": False,
            }
        ],
    }


def task_up():
    """
    Start up docker container(s).
    """

    def start_up_docker_container(target_containers, no_build):
        optional_build_arg = [] if no_build else ["--build"]
        run_docker_compose_command("up", "-d", *optional_build_arg, *target_containers)

    return {
        "actions": [start_up_docker_container],
        "pos_arg": "target_containers",
        "params": [
            {
                "name": "no_build",
                "long": "no-build",
                "type": bool,
                "default": False,
            }
        ],
    }


def task_down():
    """
    Shut down all docker containers.
    """

    def shut_down_docker_containers():
        run_docker_compose_command("down")

    return {
        "actions": [shut_down_docker_containers],
    }


def task_logs():
    """
    Display logs of a running docker container
    """

    def show_docker_logs(name):
        run_docker_compose_command("logs", "-f", *name)

    return {
        "actions": [show_docker_logs],
        "pos_arg": "name",
    }


def task_show_usage():
    """
    Display usage information.
    """

    def show_usage():
        print()
        print("  doit list                   Show all available commands.")
        print("  doit help <command>         Show usage of a specific command.")
        print("  doit help                   Display help on how to use `doit` itself.")

    return {
        "actions": [show_usage],
    }


if __name__ == "__main__":
    pass
