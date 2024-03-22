# SPDX-License-Identifier: MPL-2.0

import click
import doit.task

from ..helpers import DockerProject, run_tasks
from .build import populate_build_tasks


@click.command(name="up")
@click.option(
    "--build/--no-build",
    is_flag=True,
    default=True,
    show_default=True,
    help="(Re-)build components before starting them up.",
)
@click.option(
    "--build-deps/--no-build-deps",
    is_flag=True,
    default=True,
    show_default=True,
    help="Also build any dependencies of the given components. This option implies --build.",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def start_up_components(build: bool, build_deps: bool, dry_run: bool, components: list[str]):
    """
    Start up QCrBox components.
    """
    docker_project = DockerProject()
    components = components or docker_project.services_excluding_base_images

    if not build:
        build_deps = False

    build_tasks = []
    if build or build_deps:
        build_tasks += populate_build_tasks(components, docker_project, with_deps=build_deps, dry_run=dry_run)

    startup_task = doit.task.dict_to_task(
        {
            "name": "task_start_up_docker_containers",
            "actions": [(docker_project.start_up_docker_containers, (components, dry_run))],
        }
    )

    run_tasks(build_tasks + [startup_task])
