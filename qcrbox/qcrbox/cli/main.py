import click

from .utils_docker import get_all_services
from .utils_doit import run_tasks
from .task_build import task_build_service


@click.group()
def cli():
    """
    The Quantum Crystallography Toolbox CLI.
    """
    pass


@cli.command()
@click.option("-f", "--file", default="docker-compose.dev.yml", help="Docker compose file to search for services")
def list_services(file):
    click.echo(f"The following services are defined in the docker compose file: {file!r}")
    click.echo()
    for service in get_all_services(file):
        click.echo(f"   - {service}")


@cli.command()
@click.option("--no-deps/--with-deps", default=False)
@click.option(
    "-f",
    "--file",
    "compose_file",
    type=click.Path(exists=True),
    default="docker-compose.dev.yml",
    help="Docker compose file to search for services",
)
@click.argument("services", nargs=-1)
def build(no_deps: bool, compose_file: str, services: list[str]):
    if services == ():
        services = get_all_services(compose_file)
    click.echo(f"Building docker image for service {services!r} ({'without' if no_deps else 'including'} dependencies)")
    tasks = [task_build_service(service, deps=None) for service in services]
    run_tasks(tasks, ["run"])


if __name__ == "__main__":
    cli()
