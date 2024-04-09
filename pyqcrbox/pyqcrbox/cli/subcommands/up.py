# SPDX-License-Identifier: MPL-2.0
import sys
from typing import Optional

import click
import doit.task

from ..helpers import DockerProject, add_cli_option_to_enable_or_disable_components, add_verbose_option, run_tasks
from .build import populate_build_tasks


@click.command(name="up")
@add_cli_option_to_enable_or_disable_components
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
    build: Optional[bool],
    build_deps: Optional[bool],
    dry_run: bool,
    components: list[str],
):
    """
    Start up QCrBox components.
    """
    docker_project = DockerProject()

    def fill_default_values(build, build_deps):
        match (build, build_deps):
            case True, None:
                return True, True
            case True, True:
                return True, True
            case True, False:
                return True, False
            case False, None:
                return False, False
            case False, True:
                click.echo("Error: options --no-build and --build-deps are incompatible.")
                sys.exit(1)
            case False, False:
                return False, False
            case None, True:
                return True, True
            case None, False:
                return True, False
            case None, None:
                return True, True

    build, build_deps = fill_default_values(build, build_deps)

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
