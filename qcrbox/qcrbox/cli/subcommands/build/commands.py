# SPDX-License-Identifier: MPL-2.0

import re
from pathlib import Path

import click
from loguru import logger
from sys import platform

from ...helpers import DockerProject, get_repo_root, make_task, run_tasks


@click.command(name="build")
@click.option("--no-deps/--with-deps", default=False, help="Build given components without/with dependencies.")
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument("components", nargs=-1)
def build_components(no_deps: bool, dry_run: bool, components: list[str]):
    """
    Build QCrBox components.
    """
    docker_project = DockerProject()
    components = components or docker_project.services_including_base_images
    click.echo(
        f"Building the following components ({'without' if no_deps else 'including'} dependencies): "
        f"{', '.join(components)}\n"
    )
    tasks = populate_build_tasks(components, docker_project, with_deps=not no_deps, dry_run=dry_run)
    run_tasks(tasks)


def make_task_for_component(component_name: str, docker_project: DockerProject, with_deps: bool, dry_run: bool):
    if component_name == "qcrbox":
        task = task_build_qcrbox_python_package(dry_run)
    else:
        task = task_build_docker_image(component_name, docker_project, with_deps=with_deps, dry_run=dry_run)
    return task


def get_component_name_for_task(task):
    m = re.match("^task_build.*:(?P<component_name>.+)$")
    return m.group("component_name")


def get_build_task_name_for_component(component):
    if component == "qcrbox":
        task_name = "build_qcrbox_python_package:qcrbox"
    else:
        task_name = "build_docker_image:component"
    return task_name


@make_task
def task_build_qcrbox_python_package(dry_run: bool):
    repo_root = get_repo_root()
    qcrbox_module_root = repo_root.joinpath("qcrbox")

    actions = [lambda: logger.info("Building Python package: qcrbox", dry_run=dry_run)]
    if not dry_run:
        if platform.startswith('win'):
            base_ancestor_qcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/qcrbox_dist/")
            actions.append(
                f"cd {qcrbox_module_root} && "
                f"hatch build -t wheel && "
                f"copy /y /v dist\\qcrbox-*.whl {base_ancestor_qcrbox_dist_dir} >NUL&& "
                f"copy /y /v requirements*.txt {base_ancestor_qcrbox_dist_dir} >NUL"
            )
        else:
            base_ancestor_qcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/qcrbox_dist/").as_posix()
            action.append(
                f"cd {qcrbox_module_root.as_posix()} && "
                f"hatch build -t wheel && "
                f"cp dist/qcrbox-*.whl {base_ancestor_qcrbox_dist_dir} && "
                f"cp requirements*.txt {base_ancestor_qcrbox_dist_dir}"
            )
    return {
        "name": "task_build_python_package:qcrbox",
        "actions": actions,
    }

@make_task
def task_build_docker_image(service: str, docker_project: DockerProject, with_deps: bool, dry_run: bool):
    build_context = docker_project.get_build_context(service)
    prebuild_scripts = list(Path(build_context).glob("prebuild_*.sh"))
    logger.debug(f"Found {len(prebuild_scripts)} prebuild scripts.")
    actions = [f"cd {build_context} && bash {script.absolute()}" for script in prebuild_scripts]
    actions.append((docker_project.build_single_docker_image, (service, dry_run)))

    if with_deps:
        dependent_services = docker_project.get_direct_dependencies(service, include_build_deps=True)
        task_deps = [f"task_build_service:{dep}" for dep in dependent_services]
        if service == "base-ancestor":
            task_deps.append("task_build_python_package:qcrbox")
    else:
        task_deps = []

    return {
        "name": f"task_build_service:{service}",
        "actions": actions,
        "task_dep": task_deps,
    }


def populate_build_tasks(
    components: list[str], docker_project: DockerProject, with_deps: bool, dry_run: bool, tasks=None
):
    tasks = {}
    for component in components:
        update_build_tasks(tasks, component, docker_project, with_deps=with_deps, dry_run=dry_run)
    return list(tasks.values())


def update_build_tasks(
    existing_tasks: dict, component: str, docker_project: DockerProject, with_deps: bool, dry_run: bool
):
    if component == "qcrbox":
        new_task = task_build_qcrbox_python_package(dry_run)
    else:
        new_task = task_build_docker_image(component, docker_project, with_deps=with_deps, dry_run=dry_run)
        if with_deps:
            for dep in docker_project.get_direct_dependencies(component, include_build_deps=True):
                update_build_tasks(existing_tasks, dep, docker_project, with_deps=with_deps, dry_run=dry_run)
            if component == "base-ancestor":
                update_build_tasks(existing_tasks, "qcrbox", docker_project, with_deps=with_deps, dry_run=dry_run)

    existing_tasks[new_task.name] = new_task
