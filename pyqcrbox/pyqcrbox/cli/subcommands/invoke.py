# SPDX-License-Identifier: MPL-2.0

import json
import re
from pathlib import Path
from typing import Optional

import click
import requests

from pyqcrbox import logger, settings
from pyqcrbox.sql_models_NEW_v2 import CommandInvocationCreate


def extract_app_slug_and_version_if_present(command_name):
    m = re.match(r"^((?P<app_slug>\w+)\.((?P<app_version>.+)\.)?)?(?P<cmd_name>\w+)$", command_name)
    if not m:
        raise ValueError(f"Invalid command name: {command_name=!r}")
    return m.group("app_slug"), m.group("app_version"), m.group("cmd_name")


def extract_arg_name_and_value(arg_str: str):
    m = re.match("^([a-zA-Z_]+)=([^=]+)$", arg_str)
    if m is None:
        raise ValueError(f"Invalid argument: {arg_str!r}")
    arg_name, arg_value = m.groups()
    logger.debug(f"{arg_name=!r}, {arg_value=!r}")
    return arg_name, arg_value


@click.command(name="invoke")
@click.argument(
    "command_name",
    #metavar="<application_slug>",
)
@click.argument(
    "command_args",
    nargs=-1,
)
def invoke_command(command_name: str, command_args: list[str]):
    """
    Invoke a registered command with given arguments.
    """
    logger.debug(f"[DDD] {command_name=!r} {command_args=!r}")
    logger.warning(
        "FIXME: provide feedback on whether the arguments were provided correctly "
    )
    app_slug, app_version, cmd_name = extract_app_slug_and_version_if_present(command_name)

    cmd_args_dict = dict(extract_arg_name_and_value(arg_str) for arg_str in command_args)
    logger.debug(f"{cmd_args_dict=!r}")

    payload = CommandInvocationCreate(
        application_slug=app_slug,
        application_version=app_version,
        command_name=cmd_name,
        arguments=cmd_args_dict,
        )

    click.echo("Sending command invocation request to QCrBox")
    click.echo(f"{payload=}")

    click.echo(f"{settings.registry.server.api_url}")
    r = requests.post(settings.registry.server.api_url + "/commands/invoke", json=payload.model_dump())
    click.echo(f"{r=}")
    click.echo(r.json())
