import click
import doit.task

from ...helpers.docker_project import DockerProject
from ...helpers import (
    spin_down_docker_containers,
    get_toplevel_docker_compose_path,
    run_tasks,
    print_command_help_string_and_exit,
    exit_with_msg,
)


@click.command(name="down")
@click.option("--all", "shut_down_all_components", is_flag=True, default=False, help="Shut down all components.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def shut_down_components(shut_down_all_components: bool, dry_run: bool, components: list[str]):
    """
    Shut down QCrBox components.
    """
    dp = DockerProject(name="qcrbox")

    if components == ():
        if shut_down_all_components:
            components = dp.services
        else:
            print_command_help_string_and_exit()
    else:
        if shut_down_all_components:
            component_list = ", ".join(repr(s) for s in components)
            exit_with_msg(f"Cannot combine --all with explicit component names (here: {component_list})")

    click.echo(f"Shutting down the following components: {', '.join(components)}\n")
    task = doit.task.dict_to_task(
        {
            "name": f"task_start_up_docker_containers",
            "actions": [(dp.spin_down_docker_containers, (components,))],
        }
    )

    run_tasks([task])
