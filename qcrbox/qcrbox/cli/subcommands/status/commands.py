from typing import Optional

import click
from ...helpers import make_task, run_tasks
from ...helpers.docker_project import DockerProject


@click.command(name="status")
@click.argument("components", nargs=-1)
def get_component_status(components: list[str]):
    """
    Show status of QCrBox components.
    """
    dp = DockerProject(name="qcrbox")
    components = components or dp.services
    tasks = [task_get_status_of_docker_service(component, dp) for component in components]
    run_tasks(tasks)


@make_task
def task_get_status_of_docker_service(service: str, docker_project: DockerProject):
    return {
        "name": f"task_get_status_of_docker_service:{service}",
        "actions": [(docker_project.get_service_status, (service,))],
    }
