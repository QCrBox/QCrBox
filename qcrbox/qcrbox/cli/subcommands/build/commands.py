from pathlib import Path

import click
from ...helpers import make_task, DockerProject, get_repo_root, run_tasks
from loguru import logger


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
    tasks = populate_build_tasks(components, with_deps=not no_deps, dry_run=dry_run)
    run_tasks(tasks)


@make_task
def task_build_qcrbox_python_package(dry_run: bool):
    repo_root = get_repo_root()
    qcrbox_module_root = repo_root.joinpath("qcrbox")
    base_ancestor_qcrbox_dist_dir = repo_root.joinpath("services/base_images/base_ancestor/qcrbox_dist/").as_posix()

    actions = [lambda: logger.info("Building Python package: qcrbox", dry_run=dry_run)]
    if not dry_run:
        actions.append(
            f"cd {qcrbox_module_root.as_posix()} && "
            f"hatch build -t wheel && "
            f"cp dist/qcrbox-*.whl {base_ancestor_qcrbox_dist_dir} && "
            f"cp requirements*.txt {base_ancestor_qcrbox_dist_dir}"
        )

    return {
        "name": f"task_build_qcrbox_python_module",
        "actions": actions,
    }


@make_task
def task_build_docker_image(service: str, docker_project: DockerProject, with_deps: bool, dry_run: bool):
    dependencies = docker_project.get_dependency_chain(service, include_build_deps=True) if with_deps else []
    build_context = docker_project.get_build_context(service)
    prebuild_scripts = list(Path(build_context).glob("prebuild_*.sh"))
    logger.debug(f"[PPP] Found {len(prebuild_scripts)} prebuild scripts.")
    actions = [f"bash {script}" for script in prebuild_scripts]
    actions.append((docker_project.build_single_docker_image, (service, dry_run)))

    return {
        "name": f"task_build_service:{service}",
        "actions": actions,
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


def populate_build_tasks(components: list[str], with_deps: bool, dry_run: bool, tasks=None):
    docker_project = DockerProject()

    tasks = tasks or []

    for component in components:
        if component == "qcrbox":
            tasks.append(task_build_qcrbox_python_package(dry_run))
        else:
            if with_deps:
                for dep in docker_project.get_dependency_chain(component, include_build_deps=True):
                    if dep == "base-ancestor":
                        tasks.append(task_build_qcrbox_python_package(dry_run))
                    tasks.append(task_build_docker_image(dep, docker_project, with_deps=with_deps, dry_run=dry_run))
                if component == "base-ancestor":
                    tasks.append(task_build_qcrbox_python_package(dry_run))
            tasks.append(task_build_docker_image(component, docker_project, with_deps=with_deps, dry_run=dry_run))

    res = []
    for task in tasks:
        if task not in res:
            res.append(task)

    return res
