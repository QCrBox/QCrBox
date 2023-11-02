from typing import Optional

import click
from ...helpers import make_task, run_tasks
from ...helpers.docker_project import DockerProject
from ...helpers.docker_helpers import (
    get_status_of_docker_service,
    get_toplevel_docker_compose_path,
)


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
    dp = DockerProject(name="qcrbox")
    components = components or dp.services
    compose_file = compose_file or get_toplevel_docker_compose_path()
    tasks = [task_get_status_of_docker_service(component, compose_file) for component in components]
    run_tasks(tasks)


@make_task
def task_get_status_of_docker_service(service: str, compose_file: str):
    return {
        "name": f"task_get_status_of_docker_service:{service}",
        "actions": [(get_status_of_docker_service, (service, compose_file))],
    }
