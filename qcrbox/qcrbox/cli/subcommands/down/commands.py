import click

from qcrbox.cli.helpers.docker_helpers import get_toplevel_docker_compose_path,run_docker_compose_command


@click.command(name="down")
def shut_down_components(target_containers: list[str], dry_run: bool):
    """
    Shut down QCrBox components.
    """
    compose_file = get_toplevel_docker_compose_path()

    def shut_down_docker_containers():
        run_docker_compose_command("down", compose_file=compose_file)

    return {
        "name": f"task_shut_down_docker_containers",
        "actions": [(shut_down_docker_containers, (target_containers, dry_run))],
    }
