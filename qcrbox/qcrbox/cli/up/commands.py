import click

from ..helpers.docker_helpers import start_up_docker_containers, get_toplevel_docker_compose_path


@click.command(name="up")
def start_up_docker_containers(target_containers: list[str], rebuild_deps: bool, dry_run: bool):
    """
    Start up QCrBox components.
    """
    compose_file = get_toplevel_docker_compose_path()
    return {
        "name": f"task_start_up_docker_containers",
        "actions": [(start_up_docker_containers, (target_containers, compose_file, dry_run))],
    }
