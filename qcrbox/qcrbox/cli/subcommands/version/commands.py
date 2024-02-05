# SPDX-License-Identifier: MPL-2.0

import click

from .... import __version__


@click.command(name="version")
def print_qcrbox_version():
    """
    Print the qcrbox version.
    """
    click.echo(__version__)
