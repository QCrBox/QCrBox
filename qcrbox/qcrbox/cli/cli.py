# SPDX-License-Identifier: MPL-2.0

import click

from . import subcommands

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enables verbose mode (will print debugging messages about actions performed).",
)
@click.pass_context
def entry_point(ctx: click.core.Context, verbose: bool = False):
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    ctx.ensure_object(dict)  # ensure that ctx.obj exists and is a dict
    ctx.obj["VERBOSE"] = verbose


entry_point.add_command(subcommands.init.create_application_template)
entry_point.add_command(subcommands.build.build_components)
entry_point.add_command(subcommands.up.start_up_components)
entry_point.add_command(subcommands.down.shut_down_components)
entry_point.add_command(subcommands.list.list_qcrbox_resources)
entry_point.add_command(subcommands.invoke.invoke_command)
entry_point.add_command(subcommands.docs.docs_build_and_serve)
entry_point.add_command(subcommands.version.print_qcrbox_version)
