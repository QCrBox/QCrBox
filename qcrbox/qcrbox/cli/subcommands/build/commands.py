from pathlib import Path
from typing import Optional

import click
from ...helpers import make_task, run_tasks, print_command_help_string_and_exit, exit_with_msg, get_repo_root
from ...helpers.docker_helpers import (
    get_dependency_chain,
    build_single_docker_image,
    get_toplevel_docker_compose_path,
    get_all_services,
)
from ...logging import logger


@click.command(name="build")
@click.option("--all", "build_all_components", is_flag=True, default=False, help="Build all components.")
@click.option("--no-deps/--with-deps", default=False, help="Build given components without/with dependencies.")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default=None,
    help="Docker compose file to use.",
)
@click.argument("components", nargs=-1)
def build_components(
    build_all_components: bool, no_deps: bool, dry_run: bool, compose_file: Optional[str], components: list[str]
):
    """
    Build QCrBox components.
    """
    compose_file = compose_file or get_toplevel_docker_compose_path()

    if components == ():
        if build_all_components:
            components = get_all_services(compose_file)
        else:
            print_command_help_string_and_exit()
    else:
        if build_all_components:
            component_list = ", ".join(repr(s) for s in components)
            exit_with_msg(f"Cannot combine --all with explicit component names (here: {component_list})")

    click.echo(
        f"Building the following components ({'without' if no_deps else 'including'} dependencies): "
        f"{', '.join(components)}\n"
    )
    tasks = populate_build_tasks(components, with_deps=not no_deps, dry_run=dry_run, compose_file=compose_file)
    run_tasks(tasks)


@make_task
def task_build_qcrbox_python_package(dry_run: bool):
    repo_root = get_repo_root()
    qcrbox_module_root = repo_root.joinpath("qcrbox")
    base_ancestor_qcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/qcrbox_dist/")
    if dry_run:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [lambda: logger.info("Building Python package: qcrbox")],
        }
    else:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [
                f"cd {qcrbox_module_root.as_posix()} && "
                f"hatch build -t wheel && "
                f"cp dist/qcrbox-*.whl {base_ancestor_qcrbox_dist_dir.as_posix()}"
            ],
        }


@make_task
def task_build_docker_image(service: str, compose_file: str, with_deps: bool, dry_run: bool):
    dependencies = get_dependency_chain(service, compose_file) if with_deps else []
    return {
        "name": f"task_build_service:{service}",
        "actions": [(build_single_docker_image, (service, compose_file, dry_run))],
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


def populate_build_tasks(components: list[str], with_deps: bool, dry_run: bool, compose_file: str, tasks=None):
    tasks = tasks or []

    for component in components:
        if component == "qcrbox":
            tasks.append(task_build_qcrbox_python_package(dry_run))
        else:
            if with_deps:
                for dep in get_dependency_chain(component, compose_file):
                    if dep == "base-ancestor":
                        tasks.append(task_build_qcrbox_python_package(dry_run))
                    tasks.append(task_build_docker_image(dep, compose_file, with_deps=with_deps, dry_run=dry_run))
                if component == "base-ancestor":
                    tasks.append(task_build_qcrbox_python_package(dry_run))
            tasks.append(task_build_docker_image(component, compose_file, with_deps=with_deps, dry_run=dry_run))

    res = []
    for task in tasks:
        if task not in res:
            res.append(task)

    return res
