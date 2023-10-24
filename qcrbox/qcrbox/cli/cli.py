import click

from . import docs
from . import build


@click.group()
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


entry_point.add_command(docs.commands.docs_group)
entry_point.add_command(build.commands.build)
