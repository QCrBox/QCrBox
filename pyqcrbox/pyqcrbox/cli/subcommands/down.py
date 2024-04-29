# SPDX-License-Identifier: MPL-2.0

import click
import doit.task

from ..helpers import ClickCommandCls, DockerProject, run_tasks


@click.command(name="down", cls=ClickCommandCls)
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
    docker_project = DockerProject()
    components = components or docker_project.services_excluding_base_images
    click.echo(f"Shutting down the following components: {', '.join(components)}\n")
    task = doit.task.dict_to_task(
        {
            "name": "task_start_up_docker_containers",
            "actions": [(docker_project.spin_down_docker_containers, (components, dry_run))],
        }
    )

    run_tasks([task])
