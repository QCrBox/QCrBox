from typing import Optional

import click
from ...helpers import make_task, run_tasks, print_command_help_string_and_exit, exit_with_msg
from ...helpers.docker_helpers import (
    get_status_of_docker_service,
    get_toplevel_docker_compose_path,
    get_all_services,
)
from ...logging import logger


@click.command(name="status")
@click.option("--all", "include_all_components", is_flag=True, default=False, help="Build all components.")
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default=None,
    help="Docker compose file to use.",
)
@click.argument("components", nargs=-1)
def get_component_status(include_all_components: bool, compose_file: Optional[str], components: list[str]):
    """
    Build QCrBox components.
    """
    compose_file = compose_file or get_toplevel_docker_compose_path()

    if components == ():
        if include_all_components:
            components = get_all_services(compose_file)
        else:
            print_command_help_string_and_exit()
    else:
        if include_all_components:
            component_list = ", ".join(repr(s) for s in components)
            exit_with_msg(f"Cannot combine --all with explicit component names (here: {component_list})")

    tasks = [task_get_status_of_docker_service(component, compose_file) for component in components]
    run_tasks(tasks)


@make_task
def task_get_status_of_docker_service(service: str, compose_file: str):
    return {
        "name": f"task_get_status_of_docker_service:{service}",
        "actions": [(get_status_of_docker_service, (service, compose_file))],
    }
