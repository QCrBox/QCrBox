import click

from .utils_docker import get_all_services


@click.group()
def cli():
    """
    The Quantum Crystallography Toolbox CLI.
    """
    pass


@cli.command()
@click.option(
    "-f",
    "--file",
    default="docker-compose.dev.yml",
    help="Docker compose file to search for services"
)
def list_services(file):
    click.echo(f"The following services are defined in the docker compose file: {file!r}")
    click.echo()
    for service in get_all_services(file):
        click.echo(f"   - {service}")


if __name__ == "__main__":
    cli()
