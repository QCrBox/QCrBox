# SPDX-License-Identifier: MPL-2.0
import sys

import click
import requests

from ... import settings
from ..helpers import ClickCommandCls


@click.command(name="status", cls=ClickCommandCls)
@click.option("--json", "use_json_output", is_flag=True, help="Print output in JSON format")
@click.argument("calculation_id")
def retrieve_status(calculation_id: str, use_json_output: bool = False):
    """
    Retrieve the status of a QCrBox calculation
    """

    if not calculation_id.startswith("qcrbox_calc_"):
        click.echo(f"Invalid calculation id: {calculation_id!r}")
        sys.exit(1)

    response = requests.get(settings.registry.server.api_url + f"/calculations/{calculation_id}")
    if not response.ok:
        if response.status_code == 404:
            click.echo(f"Calculation not found: {calculation_id!r}")
            exit(1)
        data = response.json()
        click.echo("Error: could not retrieve calculation status.")
        details = data.get("detail", {"status_code": data.get("status_code", "unknown")})
        click.echo(f"Details: {details}")
        sys.exit(1)

    data = response.json()
    if use_json_output:
        click.echo(data)
    else:
        from pyqcrbox import logger

        logger.debug(data)
        click.echo(f"Calculation id: {data['calculation_id']}")
        click.echo(f"Status: {data['status']}")
        if data["extra_info"] != {}:
            click.echo(f"Extra info: {data['extra_info']}")
        click.echo()
        click.echo("Stdout:")
        click.echo("-------")
        click.echo()
        click.echo(data["stdout"] or "<no output>")
        click.echo()
        click.echo("Stderr:")
        click.echo("-------")
        click.echo()
        click.echo(data["stderr"] or "<no output>")
