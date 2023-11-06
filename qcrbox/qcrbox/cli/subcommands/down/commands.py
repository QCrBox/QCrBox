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
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def shut_down_components(dry_run: bool, components: list[str]):
    """
    Shut down QCrBox components.
    """
    docker_project = DockerProject(name="qcrbox")
    components = components or docker_project.services_excluding_base_images
    click.echo(f"Shutting down the following components: {', '.join(components)}\n")
    task = doit.task.dict_to_task(
        {
            "name": f"task_start_up_docker_containers",
            "actions": [(docker_project.spin_down_docker_containers, (components, dry_run))],
        }
    )

    run_tasks([task])
