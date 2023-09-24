import click

from .utils_docker import get_all_services, get_dependency_chain
from .utils_doit import run_tasks
from .task_build import task_build_docker_service, task_build_qcrbox_python_package


@click.group()
def cli():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


@cli.command()
@click.option("-f", "--file", default="docker-compose.dev.yml", help="Docker compose file to search for services")
def list_services(file: str):
    click.echo(f"Services defined in {file!r}:")
    click.echo()
    for service in get_all_services(file):
        click.echo(f"   - {service}")


@cli.command()
@click.option("--no-deps/--with-deps", default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default="docker-compose.dev.yml",
    help="Docker compose file to search for services",
)
@click.argument("services", nargs=-1)
def build(no_deps: bool, dry_run: bool, compose_file: str, services: list[str]):
    """
    Build QCrBox component(s).
    """
    if services == ():
        services = get_all_services(compose_file)

    click.echo(
        f"Building the following components ({'without' if no_deps else 'including'} dependencies): "
        f"{', '.join(services)}"
    )
    tasks = []
    for service in services:
        if service == "qcrbox":
            tasks.append(task_build_qcrbox_python_package(dry_run))
        else:
            if not no_deps:
                for dep in get_dependency_chain(service, compose_file):
                    if dep == "base-ancestor":
                        tasks.append(task_build_qcrbox_python_package(dry_run))
                    tasks.append(task_build_docker_service(dep, compose_file, with_deps=not no_deps, dry_run=dry_run))
                if service == "base-ancestor":
                    tasks.append(task_build_qcrbox_python_package(dry_run))
            tasks.append(task_build_docker_service(service, compose_file, with_deps=not no_deps, dry_run=dry_run))
    run_tasks(tasks, ["run"])


if __name__ == "__main__":
    cli()
