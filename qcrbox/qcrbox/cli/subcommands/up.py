# SPDX-License-Identifier: MPL-2.0
import sys
from typing import Optional

import click
import doit.task

from ..helpers import DockerProject, add_cli_option_enable_disable_components, add_verbose_option, run_tasks
from ..helpers.cli_helpers import determine_components_to_include
from .build import populate_build_tasks


@click.command(name="up")
@add_cli_option_enable_disable_components
@click.option(
    "--build/--no-build",
    is_flag=True,
    default=None,
    help="Build each given component before starting it up. [default: True]",
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
    include_all_components: bool,
    enabled_components: list[str],
    disabled_components: list[str],
    build: Optional[bool],
    build_deps: Optional[bool],
    dry_run: bool,
    components: list[str],
):
    """
    Start up QCrBox components.
    """
    docker_project = DockerProject()
    components = components or docker_project.services_excluding_base_images

    components_to_include = determine_components_to_include(
        docker_project, include_all_components, enabled_components, disabled_components, components
    )

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
        build_tasks += populate_build_tasks(
            components_to_include, docker_project, with_deps=build_deps, dry_run=dry_run
        )

    startup_task = doit.task.dict_to_task(
        {
            "name": "task_start_up_docker_containers",
            "actions": [(docker_project.start_up_docker_containers, (components_to_include, dry_run))],
        }
    )

    run_tasks(build_tasks + [startup_task])
