import click
from ...helpers import make_task, run_tasks, get_repo_root
from ...helpers.docker_project import DockerProject
from ...logging import logger


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
def build_components(
    no_deps: bool, dry_run: bool, components: list[str]
):
    """
    Build QCrBox components.
    """
    docker_project = DockerProject(name="qcrbox")
    components = components or docker_project.services
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
def task_build_docker_image(service: str, docker_project: DockerProject, with_deps: bool, dry_run: bool):
    dependencies = docker_project.get_dependency_chain(service) if with_deps else []
    return {
        "name": f"task_build_service:{service}",
        "actions": [(docker_project.build_single_docker_image, (service, dry_run))],
        "task_dep": [f"task_build_service:{dep}" for dep in dependencies],
    }


def populate_build_tasks(components: list[str], with_deps: bool, dry_run: bool, tasks=None):
    docker_project = DockerProject(name="qcrbox")

    tasks = tasks or []

    for component in components:
        if component == "qcrbox":
            tasks.append(task_build_qcrbox_python_package(dry_run))
        else:
            if with_deps:
                for dep in docker_project.get_dependency_chain(component):
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
