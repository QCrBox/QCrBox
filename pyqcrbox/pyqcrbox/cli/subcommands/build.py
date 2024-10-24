# SPDX-License-Identifier: MPL-2.0
import shutil
from pathlib import Path
from typing import Iterable

import click
from doit.task import Task
from loguru import logger

from ..helpers import (
    ClickCommandCls,
    DockerProject,
    add_cli_option_to_enable_or_disable_components,
    add_verbose_option,
    get_repo_root,
    make_task,
    run_tasks,
)
from ..helpers.compose_file_config import QCrBoxNoBuildContextError


@click.command(name="build", cls=ClickCommandCls)
@add_cli_option_to_enable_or_disable_components
@click.option("--no-deps/--with-deps", default=False, help="Build given components without/with dependencies.")
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@add_verbose_option
@click.argument("components", nargs=-1)
def build_components(
    no_deps: bool,
    dry_run: bool,
    components: list[str],
):
    """
    Build QCrBox components.
    """
    docker_project = DockerProject()

    action_descr = "Building" if not dry_run else "Would build"
    click.echo(
        f"{action_descr} the following components ({'without' if no_deps else 'including'} dependencies): "
        f"{', '.join(components)}\n"
    )
    tasks = populate_build_tasks(components, docker_project, with_deps=not no_deps, dry_run=dry_run)
    run_tasks(tasks)


def make_action_to_copy_file(src, dest):
    def action_copy_file():
        # logger.debug(f"Copying file: {src} -> {dest}")
        shutil.copy(src, dest)

    return action_copy_file


def make_action_to_build_wheel(package_root, output_dir):
    cmd = f"cd {package_root} && uv build --wheel --out-dir {output_dir}"
    return cmd


@make_task
def task_clone_qcrboxtools_repo(dry_run: bool):
    qcrboxtools_repo_url = "https://github.com/QCrBox/QCrBoxTools.git"
    repo_root = get_repo_root()
    target_dir = repo_root.joinpath(".build", "QCrBoxTools")
    action_descr = "Pulling/cloning" if not dry_run else "Would pull/clone"
    actions = [lambda: logger.info(f"{action_descr} QCrBoxTools repo in {target_dir} ...", dry_run=dry_run)]
    if not dry_run:
        actions.append(f"git -C {target_dir} pull || git clone {qcrboxtools_repo_url} {target_dir}")
    return {"name": "task_clone_repo:qcrboxtools", "actions": actions}


@make_task
def task_build_pyqcrbox_python_package(dry_run: bool):
    repo_root = get_repo_root()

    action_descr = "Building" if not dry_run else "Would build"
    actions = [lambda: logger.info(f"{action_descr} Python package: pyqcrbox", dry_run=dry_run)]
    if not dry_run:
        pyqcrbox_package_root = repo_root.joinpath("pyqcrbox")
        base_ancestor_pyqcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/pyqcrbox_dist/")
        requirements_files = list(repo_root.glob("pyqcrbox/requirements*.txt"))

        action_build_pyqcrbox_wheel = make_action_to_build_wheel(pyqcrbox_package_root, base_ancestor_pyqcrbox_dist_dir)
        actions_copy_requirements_files = [
            make_action_to_copy_file(filename, base_ancestor_pyqcrbox_dist_dir) for filename in requirements_files
        ]

        actions += [action_build_pyqcrbox_wheel]
        actions += actions_copy_requirements_files

    return {
        "name": "task_build_python_package:pyqcrbox",
        "actions": actions,
    }


@make_task
def task_build_qcrboxtools_python_package(dry_run: bool):
    repo_root = get_repo_root()

    action_descr = "Building" if not dry_run else "Would build"
    actions = [lambda: logger.info(f"{action_descr} Python package: qcrboxtools", dry_run=dry_run)]
    if not dry_run:
        qcrboxtools_package_root = repo_root.joinpath(".build", "QCrBoxTools")
        base_ancestor_pyqcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/pyqcrbox_dist/")
        # requirements_files = list(qcrboxtools_package_root.glob("requirements*.txt"))

        action_build_qcrboxtools_wheel = make_action_to_build_wheel(
            qcrboxtools_package_root, base_ancestor_pyqcrbox_dist_dir
        )
        # actions_copy_requirements_files = [
        #     make_action_to_copy_file(filename, base_ancestor_pyqcrbox_dist_dir) for filename in requirements_files
        # ]

        actions += [action_build_qcrboxtools_wheel]
        # actions += actions_copy_requirements_files

    return {
        "name": "task_build_python_package:qcrboxtools",
        "actions": actions,
        "task_dep": ["task_clone_repo:qcrboxtools"],
    }


@make_task
def task_build_docker_image(service: str, docker_project: DockerProject, with_deps: bool, dry_run: bool):
    actions = []

    task_deps = []
    if with_deps:
        dependent_services = docker_project.get_direct_dependencies(service, include_build_deps=True)
        task_deps = [f"task_build_service:{dep}" for dep in dependent_services]
        if service == "base-ancestor":
            task_deps.append("task_build_python_package:pyqcrbox")

    try:
        build_context = docker_project.get_build_context(service)

        prebuild_scripts = sorted(Path(build_context).glob("prebuild_*.py"))
        if prebuild_scripts != []:
            logger.debug(f"Found {len(prebuild_scripts)} prebuild script(s) for {service!r}")
            if not dry_run:
                actions += [f"cd {build_context} && python {script.absolute()}" for script in prebuild_scripts]

        actions.append((docker_project.build_single_docker_image, (service, dry_run)))
    except QCrBoxNoBuildContextError:
        logger.debug(f"No local build context found for service {service!r}, nothing to do.")

    return {
        "name": f"task_build_service:{service}",
        "actions": actions,
        "task_dep": task_deps,
    }


def populate_build_tasks(
    components: Iterable[str], docker_project: DockerProject, with_deps: bool, dry_run: bool, tasks=None
) -> list[Task]:
    tasks = {}
    for component in components:
        update_build_tasks(tasks, component, docker_project, with_deps=with_deps, dry_run=dry_run)
    return list(tasks.values())


def update_build_tasks(
    existing_tasks: dict, component: str, docker_project: DockerProject, with_deps: bool, dry_run: bool
) -> None:
    if component == "pyqcrbox":
        new_tasks = [
            task_build_pyqcrbox_python_package(dry_run),
        ]
    elif component == "pyqcrboxtools":
        new_tasks = [
            task_clone_qcrboxtools_repo(dry_run),
            task_build_qcrboxtools_python_package(dry_run),
        ]
    else:
        new_tasks = [task_build_docker_image(component, docker_project, with_deps=with_deps, dry_run=dry_run)]
        if with_deps:
            for dep in docker_project.get_direct_dependencies(component, include_build_deps=True):
                update_build_tasks(existing_tasks, dep, docker_project, with_deps=with_deps, dry_run=dry_run)
            if component == "base-ancestor":
                update_build_tasks(existing_tasks, "pyqcrbox", docker_project, with_deps=with_deps, dry_run=dry_run)
                update_build_tasks(
                    existing_tasks, "pyqcrboxtools", docker_project, with_deps=with_deps, dry_run=dry_run
                )

    for task in new_tasks:
        existing_tasks[task.name] = task
