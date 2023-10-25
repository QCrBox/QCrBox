import click
import doit.task

from ..helpers import run_tasks
from ..helpers.docker_helpers import get_toplevel_docker_compose_path, get_all_services


@click.command(name="info")
@click.option("-l", "--list-components/--no-list-components", is_flag=True, type=bool, default=True)
def show_info(list_components: bool):
    """
    Show information on QCrBox components.
    """
    tasks = []

    if list_components:
        tasks.append(
            doit.task.dict_to_task(
                {
                    "name": "list-components",
                    "actions": [print_list_of_components],
                }
            )
        )

    run_tasks(tasks)


def print_list_of_components():
    compose_file = get_toplevel_docker_compose_path()
    click.echo()
    click.echo(f"Components defined in {compose_file.as_posix()!r}:")
    click.echo()
    for service in get_all_services(compose_file):
        click.echo(f"   - {service}")
