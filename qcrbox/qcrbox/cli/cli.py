import click

from .build.commands import build
from .docs.commands import docs_group
from .info.commands import info_group


@click.group()
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


entry_point.add_command(docs_group)
entry_point.add_command(build)
entry_point.add_command(info_group)
