from typing import Optional

import click
from ...helpers import make_task, run_tasks, print_command_help_string_and_exit, exit_with_msg
from ...helpers.docker_project import DockerProject
from ...helpers.docker_helpers import (
    get_all_services,
    get_status_of_docker_service,
    get_toplevel_docker_compose_path,
)
from ...logging import logger


@click.command(name="status")
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default=None,
    help="Docker compose file to use.",
)
@click.argument("components", nargs=-1)
def get_component_status(compose_file: Optional[str], components: list[str]):
    """
    Show status of QCrBox components.
    """
    compose_file = compose_file or get_toplevel_docker_compose_path()
    dp = DockerProject("qcrbox", compose_file)
    components = components or dp.services
    tasks = [task_get_status_of_docker_service(component, compose_file) for component in components]
    run_tasks(tasks)


@make_task
def task_get_status_of_docker_service(service: str, compose_file: str):
    return {
        "name": f"task_get_status_of_docker_service:{service}",
        "actions": [(get_status_of_docker_service, (service, compose_file))],
    }
