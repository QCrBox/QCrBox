from pathlib import Path
from typing import Optional

import click
from loguru import logger
from ..helpers import make_task, run_tasks, print_command_help_string_and_exit, exit_with_msg
from ..helpers.docker_helpers import (
    get_dependency_chain,
    build_single_docker_image,
    get_toplevel_docker_compose_path,
    get_all_services,
)


@click.command()
@click.option("--all", "build_all_services", is_flag=True, default=False)
@click.option("--no-deps/--with-deps", default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default=None,
    help="Docker compose file to use",
)
@click.argument("services", nargs=-1)
def build(build_all_services: bool, no_deps: bool, dry_run: bool, compose_file: Optional[str], services: list[str]):
    """
    Build QCrBox components.
    """
    compose_file = compose_file or get_toplevel_docker_compose_path()

    if services == ():
        if build_all_services:
            services = get_all_services(compose_file)
        else:
            print_command_help_string_and_exit()
    else:
        if build_all_services:
            services_list = ', '.join(repr(s) for s in services)
            exit_with_msg(f"Cannot combine --all with explicit service names (here: {services_list})")

    click.echo(
        f"Building the following components ({'without' if no_deps else 'including'} dependencies): "
        f"{', '.join(services)}"
    )
    tasks = populate_build_tasks(services, with_deps=not no_deps, dry_run=dry_run, compose_file=compose_file)
    run_tasks(tasks)


@make_task
def task_build_qcrbox_python_package(dry_run: bool):
    qcrbox_module_root = Path(__file__).parent.parent.parent.parent
    if dry_run:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [lambda: logger.debug("Building Python package: 'qcrbox'")],
        }
    else:
        return {
            "name": f"task_build_qcrbox_python_module",
            "actions": [
                f"cd {qcrbox_module_root.as_posix()} && "
                f"hatch build -t wheel && "
                f"cp dist/qcrbox-*.whl ../services/base_images/base_ancestor/"
            ],
        }


@make_task
def task_build_docker_service(service: str, compose_file: str, with_deps: bool, dry_run: bool):
    dependencies = get_dependency_chain(service, compose_file) if with_deps else []
    return {
        "name": f"task_build_service:{service}",
        "actions": [(build_single_docker_image, (service, compose_file, dry_run))],
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


def populate_build_tasks(services: list[str], with_deps: bool, dry_run: bool, compose_file: str, tasks=None):
    tasks = tasks or []

    for service in services:
        if service == "qcrbox":
            tasks.append(task_build_qcrbox_python_package(dry_run))
        else:
            if with_deps:
                for dep in get_dependency_chain(service, compose_file):
                    if dep == "base-ancestor":
                        tasks.append(task_build_qcrbox_python_package(dry_run))
                    tasks.append(task_build_docker_service(dep, compose_file, with_deps=with_deps, dry_run=dry_run))
                if service == "base-ancestor":
                    tasks.append(task_build_qcrbox_python_package(dry_run))
            tasks.append(task_build_docker_service(service, compose_file, with_deps=with_deps, dry_run=dry_run))

    res = []
    for task in tasks:
        if task not in res:
            res.append(task)

    return res
