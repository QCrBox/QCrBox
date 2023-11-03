import click
import doit.task

from qcrbox.cli.helpers import run_tasks, DockerProject


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
    dp = DockerProject(name="qcrbox")
    dp.print_list_of_components(print_func=click.echo)
