# SPDX-License-Identifier: MPL-2.0

import click

from . import subcommands
from .helpers import NaturalOrderGroup, add_verbose_option

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}


@click.group(context_settings=CONTEXT_SETTINGS, cls=NaturalOrderGroup)
@add_verbose_option
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


# entry_point.add_command(subcommands.init.create_application_template)
entry_point.add_command(subcommands.build.build_components)
entry_point.add_command(subcommands.up.start_up_components)
entry_point.add_command(subcommands.down.shut_down_components)
entry_point.add_command(subcommands.list.list_qcrbox_resources)
entry_point.add_command(subcommands.init.create_application_template)
entry_point.add_command(subcommands.invoke.invoke_command)
entry_point.add_command(subcommands.status.retrieve_status)
entry_point.add_command(subcommands.docs.docs_build_and_serve)
entry_point.add_command(subcommands.dev.dev_commands)
entry_point.add_command(subcommands.version.print_qcrbox_version)
