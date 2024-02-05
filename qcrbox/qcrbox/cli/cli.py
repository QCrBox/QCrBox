# SPDX-License-Identifier: MPL-2.0

import click

from . import subcommands


@click.group()
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


entry_point.add_command(subcommands.build.build_components)
entry_point.add_command(subcommands.up.start_up_components)
entry_point.add_command(subcommands.down.shut_down_components)
entry_point.add_command(subcommands.list.list_qcrbox_resources)
entry_point.add_command(subcommands.invoke.invoke_command)
entry_point.add_command(subcommands.docs.docs_build_and_serve)
entry_point.add_command(subcommands.version.print_qcrbox_version)
