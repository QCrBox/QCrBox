import click
import doit.task

from ...helpers import start_up_docker_containers, get_toplevel_docker_compose_path, run_tasks


@click.command(name="up")
@click.option(
    "--rebuild-deps/--no-rebuild-deps",
    is_flag=True,
    default=False,
    help="Rebuild dependencies before starting up the given components.",
)
@click.option(
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
    compose_file = get_toplevel_docker_compose_path()
    task =  doit.task.dict_to_task({
        "name": f"task_start_up_docker_containers",
        "actions": [(start_up_docker_containers, (components, compose_file, dry_run))],
    })

    run_tasks([task])
