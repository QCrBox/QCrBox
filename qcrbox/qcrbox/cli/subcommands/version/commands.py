import click

from .... import __version__

@click.command(name="version")
def print_qcrbox_version():
    """
    Print the qcrbox version.
    """
    click.echo(__version__)
