import click
import doit.task

from ..build.commands import populate_build_tasks
from ...helpers import start_up_docker_containers, run_tasks, DockerProject


@click.command(name="up")
@click.option(
    "--rebuild-deps/--no-rebuild-deps",
    is_flag=True,
    default=True,
    help="Rebuild dependencies before starting up the given components.",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def start_up_components(rebuild_deps: bool, dry_run: bool, components: list[str]):
    """
    Start up QCrBox components.
    """
    docker_project = DockerProject(name="qcrbox")
    components = components or docker_project.services

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
