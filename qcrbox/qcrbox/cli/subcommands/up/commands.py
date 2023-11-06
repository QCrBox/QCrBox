import click
import doit.task

from ..build.commands import populate_build_tasks
from ...helpers import (
    start_up_docker_containers,
    run_tasks,
    DockerProject,
    print_command_help_string_and_exit,
    exit_with_msg,
)


@click.command(name="up")
@click.option("--all", "start_up_all_components", is_flag=True, default=False, help="Start up all components.")
@click.option(
    "--rebuild-deps/--no-rebuild-deps",
    is_flag=True,
    default=True,
    help="Rebuild dependencies before starting up the given components.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def start_up_components(start_up_all_components: bool, rebuild_deps: bool, dry_run: bool, components: list[str]):
    """
    Start up QCrBox components.
    """
    docker_project = DockerProject(name="qcrbox")

    if components == ():
        if start_up_all_components:
            components = docker_project.services
        else:
            print_command_help_string_and_exit()
    else:
        if start_up_all_components:
            component_list = ", ".join(repr(s) for s in components)
            exit_with_msg(f"Cannot combine --all with explicit component names (here: {component_list})")

    build_tasks = []
    if rebuild_deps:
        build_tasks += populate_build_tasks(components, with_deps=True, dry_run=dry_run)

    startup_task = doit.task.dict_to_task(
        {
            "name": f"task_start_up_docker_containers",
            "actions": [(start_up_docker_containers, (components, docker_project, dry_run))],
        }
    )

    run_tasks(build_tasks + [startup_task])
