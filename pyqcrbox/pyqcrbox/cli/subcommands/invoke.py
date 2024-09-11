# SPDX-License-Identifier: MPL-2.0
import re
import sys

import click
import requests

from pyqcrbox.sql_models import CommandInvocationCreate

from ... import settings
from ..helpers import ClickCommandCls


@click.command(name="invoke", cls=ClickCommandCls)
@click.option("--application-slug")
@click.option("--application-version")
@click.argument("command_name")
@click.argument("command_args", nargs=-1)
def invoke_command(command_name: str, command_args: list[str], application_slug: str, application_version: str):
    """
    Invoke command with given arguments.
    """

    def parse_arg(arg_str):
        m = re.match(r"^(?P<arg_name>\w+)=(?P<value>.+)", arg_str)
        if not m:
            raise ValueError(f"Invalid argument: {arg_str!r}")
        return m.group("arg_name"), m.group("value")

    arguments = {arg_name: value for (arg_name, value) in [parse_arg(arg_str) for arg_str in command_args]}

    click.echo(f"Invoking command {command_name!r} with arguments: {arguments}")
    cmd = CommandInvocationCreate(
        application_slug=application_slug,
        application_version=application_version,
        command_name=command_name,
        arguments=arguments,
    )
    response = requests.post(
        settings.registry.server.api_url + "commands/invoke",
        cmd.model_dump_json().encode(),
    )
    if not response.ok:
        data = response.json()
        click.echo("Error: command invocation failed.")
        click.echo(f"Details: {data['detail']}")
        sys.exit(1)
    click.echo(response.json())
