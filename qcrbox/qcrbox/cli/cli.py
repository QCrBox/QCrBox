import click

from . import subcommands

@click.group()
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


entry_point.add_command(subcommands.docs_build_and_serve)
entry_point.add_command(subcommands.build_components)
entry_point.add_command(subcommands.show_info)
entry_point.add_command(subcommands.start_up_components)
entry_point.add_command(subcommands.shut_down_components)
entry_point.add_command(subcommands.get_component_status)