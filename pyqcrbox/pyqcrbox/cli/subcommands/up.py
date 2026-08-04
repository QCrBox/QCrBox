# SPDX-License-Identifier: MPL-2.0
import os
import sys

import click
import doit.task

from ..helpers import (
    ClickCommandCls,
    DockerProject,
    add_cli_option_to_enable_or_disable_components,
    add_verbose_option,
    run_tasks,
)
from .build import populate_build_tasks
from .register import register_specs_for_components


def _fill_default_build_values(build, build_deps):
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


def warn_if_orchestrator_disabled(docker_project: DockerProject):
    """Warn when on-demand mode is used while the orchestrator is disabled.

    In that state, registered applications would never be spawned.
    """
    value = os.environ.get("QCRBOX__ORCHESTRATOR__ENABLED")
    if value is None:
        env_file_name = ".env.prod" if docker_project.config_name == "prebuilt" else ".env.dev"
        env_file = docker_project.repo_root.joinpath(env_file_name)
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("QCRBOX__ORCHESTRATOR__ENABLED="):
                value = line.split("=", 1)[1].strip().strip("'\"")
    if (value or "").lower() != "true":
        click.echo(
            "Warning: QCRBOX__ORCHESTRATOR__ENABLED is not set to 'true' in the active "
            "environment, so the registry will not spawn application containers on "
            "demand. Registered applications will be unusable until the orchestrator "
            "is enabled (or their containers are started with 'qcb up')."
        )


def run_startup_tasks(
    *,
    build: bool | None,
    build_deps: bool | None,
    prebuilt_images: bool | None,
    dry_run: bool,
    project_name: str,
    components: list[str],
    on_demand: bool = False,
):
    """Implement `qcb up` and `qcb serve` startup behavior.

    Serve mode starts core and always-on services; application containers are
    spawned on demand.
    """
    build, build_deps = _fill_default_build_values(build, build_deps)
    docker_project = DockerProject(name=project_name, config_name="prebuilt" if prebuilt_images else "development")

    if on_demand:
        warn_if_orchestrator_disabled(docker_project)

    build_tasks = []
    if build or build_deps:
        build_tasks += populate_build_tasks(components, docker_project, with_deps=build_deps, dry_run=dry_run)

    if on_demand:
        startup_action = (docker_project.start_up_serving_services, (components, dry_run))
    else:
        startup_action = (docker_project.start_up_docker_containers, (components, dry_run))

    startup_task = doit.task.dict_to_task(
        {
            "name": "task_start_up_docker_containers",
            "actions": [startup_action],
        }
    )

    tasks = build_tasks + [startup_task]

    if not dry_run:
        # Best-effort: once the registry is healthy, push the application specs
        # of the selected components so they are listed even before (or without)
        # their containers self-registering. In on-demand mode this is what
        # makes the applications spawnable (spec + docker_image in the DB).
        register_specs_task = doit.task.dict_to_task(
            {
                "name": "task_register_application_specs",
                "actions": [(register_specs_for_components, (docker_project, list(components)))],
                "task_dep": ["task_start_up_docker_containers"],
            }
        )
        tasks.append(register_specs_task)

    run_tasks(tasks)


@click.command(name="up", cls=ClickCommandCls)
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
    "--prebuilt-images",
    is_flag=True,
    default=False,
    help="Use pre-built production-ready images from the QCrBox container registry. [default: False]",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.option(
    "-p",
    "--project-name",
    default="qcrbox",
    help="Docker project name (see https://docs.docker.com/compose/project-name/)",
)
@add_verbose_option
@click.argument("components", nargs=-1)
def start_up_components(
    build: bool | None,
    build_deps: bool | None,
    prebuilt_images: bool | None,
    dry_run: bool,
    project_name: str,
    components: list[str],
):
    """Start up QCrBox components."""
    run_startup_tasks(
        build=build,
        build_deps=build_deps,
        prebuilt_images=prebuilt_images,
        dry_run=dry_run,
        project_name=project_name,
        components=components,
    )


@click.command(name="serve", cls=ClickCommandCls)
@add_cli_option_to_enable_or_disable_components
@click.option(
    "--build/--no-build",
    is_flag=True,
    default=None,
    help="Build each given component before registering it. [default: True]",
)
@click.option(
    "--build-deps/--no-build-deps",
    is_flag=True,
    default=None,
    help="Also build any dependencies of the given components. This option implies --build. [default: --build-deps]",
)
@click.option(
    "--prebuilt-images",
    is_flag=True,
    default=False,
    help="Use pre-built production-ready images from the QCrBox container registry. [default: False]",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.option(
    "-p",
    "--project-name",
    default="qcrbox",
    help="Docker project name (see https://docs.docker.com/compose/project-name/)",
)
@add_verbose_option
@click.argument("components", nargs=-1)
def serve_components(
    build: bool | None,
    build_deps: bool | None,
    prebuilt_images: bool | None,
    dry_run: bool,
    project_name: str,
    components: list[str],
):
    """Build and register applications for on-demand QCrBox service.

    Only core and selected always-on services start immediately. Application
    containers are spawned by the registry orchestrator, which requires
    QCRBOX__ORCHESTRATOR__ENABLED=true.

    Use 'qcb up' instead for container development, where the selected
    application containers are started directly and stay running.
    """
    run_startup_tasks(
        build=build,
        build_deps=build_deps,
        prebuilt_images=prebuilt_images,
        dry_run=dry_run,
        project_name=project_name,
        components=components,
        on_demand=True,
    )
