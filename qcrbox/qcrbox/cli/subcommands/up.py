# SPDX-License-Identifier: MPL-2.0
import sys
from typing import Optional

import click
import doit.task

from ...logging import set_cli_log_level
from ..helpers import DockerProject, add_verbose_option, run_tasks
from .build import populate_build_tasks


@click.command(name="up")
@click.option(
    "--build/--no-build",
    is_flag=True,
    default=None,
    help="(Re-)build components before starting them up. [default: True]",
)
@click.option(
    "--build-deps/--no-build-deps",
    is_flag=True,
    default=None,
    help="Also build any dependencies of the given components. This option implies --build. [default: --build-deps]",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@add_verbose_option
@click.argument("components", nargs=-1)
def start_up_components(
    ctx: click.core.Context,
    build: Optional[bool],
    build_deps: Optional[bool],
    dry_run: bool,
    components: list[str],
    verbose: bool,
):
    """
    Start up QCrBox components.
    """
    if ctx.obj["VERBOSE"] or verbose:
        set_cli_log_level("DEBUG")

    docker_project = DockerProject()
    components = components or docker_project.services_excluding_base_images

    if build is None:
        build = True
    elif build is False:
        if build_deps is None:
            build_deps = False
        elif build_deps is True:
            click.echo("Error: options --no-build and --build-deps are incompatible.")
            sys.exit(1)
        else:
            pass
    elif build is True:
        if build_deps is None:
            build_deps = True
    else:
        raise ValueError(f"Invalid value for --build flag: {build}")

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
