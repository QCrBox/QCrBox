# SPDX-License-Identifier: MPL-2.0

import click

from ..helpers import ClickCommandCls, get_current_pyqcrbox_version


@click.command(name="version", cls=ClickCommandCls)
def print_qcrbox_version():
    """Print the pyqcrbox version."""
    click.echo(get_current_pyqcrbox_version())
