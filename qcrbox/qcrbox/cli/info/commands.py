import click
import doit.task

from ..helpers import run_tasks
from ..helpers.docker_helpers import get_toplevel_docker_compose_path, get_all_services


@click.group(name="info")
def info_group():
    """
    Show information on QCrBox components.
    """
    pass


@info_group.command()
def components():
    task = doit.task.dict_to_task(
        {
            "name": "list-components",
            "actions": [list_components],
        }
    )
    run_tasks([task])


def list_components():
    compose_file = get_toplevel_docker_compose_path()
    click.echo()
    click.echo(f"Components defined in {compose_file.as_posix()!r}:")
    click.echo()
    for service in get_all_services(compose_file):
        click.echo(f"   - {service}")
