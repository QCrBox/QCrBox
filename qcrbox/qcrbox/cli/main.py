import click

from .utils_docker import get_all_services, get_dependency_chain
from .utils_doit import run_tasks
from .task_build import task_build_docker_service, populate_build_tasks
from .task_up import task_start_up_docker_containers
from .task_down import task_spin_down_docker_containers


@click.group()
def cli():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


@cli.command()
@click.option("-f", "--file", default="docker-compose.dev.yml", help="Docker compose file to use")
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
    help="Docker compose file to use",
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
    tasks = populate_build_tasks(services, with_deps=not no_deps, dry_run=dry_run, compose_file=compose_file)
    run_tasks(tasks, ["run"])


@cli.command(name="up")
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default="docker-compose.dev.yml",
    help="Docker compose file to use",
)
@click.option("--rebuild-deps/--no-rebuild-deps", default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.argument("services", nargs=-1)
def start_up_docker_services(compose_file: str, rebuild_deps: bool, dry_run: bool, services: list[str]):
    """
    Start up QCrBox component(s).
    """
    if services == ():
        services = get_all_services(compose_file)

    if not rebuild_deps:
        tasks = []
    else:
        tasks = populate_build_tasks(services, with_deps=True, dry_run=dry_run, compose_file=compose_file)

    tasks.append(task_start_up_docker_containers(services, compose_file, rebuild_deps=rebuild_deps, dry_run=dry_run))
    run_tasks(tasks, ["run"])


@cli.command(name="down")
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default="docker-compose.dev.yml",
    help="Docker compose file to use",
)
def spin_down_docker_services(compose_file: str):
    """
    Spin down all QCrBox component(s).
    """
    tasks = []
    tasks.append(task_spin_down_docker_containers(compose_file))
    run_tasks(tasks, ["run"])


if __name__ == "__main__":
    cli()
