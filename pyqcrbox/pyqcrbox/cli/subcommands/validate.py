# SPDX-License-Identifier: MPL-2.0
import sys

import pydantic
import yaml

from pathlib import Path

import click

from pyqcrbox.sql_models_NEW_v2 import ApplicationSpec
from pyqcrbox.sql_models_NEW_v2.command_spec import ImplementedAs
from ..helpers import ClickCommandCls


def prettify_pydantic_validation_error(yaml_data: dict, err_details: dict):
    loc = err_details["loc"]
    err_type = err_details["type"]
    msg = err_details["msg"]

    match loc, err_type, msg:
        case ("qcrbox_yaml_spec_version",), "missing", _:
            msg = "- Missing toplevel field: 'qcrbox_yaml_spec_version'"
        case _, _, "Unable to extract tag using discriminator 'dtype'":
            assert loc[0] == "commands"
            assert loc[2] in ImplementedAs
            assert loc[3] == "parameters"
            cmd_idx = loc[1]
            param_idx = loc[4]
            cmd_data = yaml_data["commands"][cmd_idx]
            cmd_name = cmd_data["name"]
            param_data = cmd_data["parameters"][param_idx]
            param_name = param_data["name"]
            if "type" in param_data:
                msg = f"- Unrecognised field 'type' in definition of command: {cmd_name!r}, parameter: {param_name!r}"
                msg += "\n  Did you mean 'dtype'?"
            else:
                msg = f"- Missing field 'dtype' in definition of command: {cmd_name!r}, parameter: {param_name!r}"
        case _:
            msg = None

    return msg


@click.command(name="validate", cls=ClickCommandCls)
@click.argument("application_spec_file", type=click.Path(exists=True))
@click.option(
    "--show-pydantic-errors",
    is_flag=True,
    default=False,
    help="Display the original pydantic validation error (for debugging).",
)
def validate_application_spec(application_spec_file: click.Path, show_pydantic_errors: bool):
    """
    Check application spec yaml file for errors.
    """
    all_errors_recognised = True

    try:
        _ = ApplicationSpec.from_yaml_file(application_spec_file)
    except pydantic.ValidationError as exc:
        click.echo(f"❌ Yaml spec failed to validate: {application_spec_file!r}")
        click.echo()
        yaml_data = yaml.safe_load(open(application_spec_file).read())
        for err_details in exc.errors():
            err_msg = prettify_pydantic_validation_error(yaml_data, err_details)
            if err_msg:
                click.echo(err_msg)
            else:
                all_errors_recognised = False

        if show_pydantic_errors or not all_errors_recognised:
            click.echo()
            click.echo(f"Original error:")
            click.echo()
            click.echo(exc)

        sys.exit(1)

    click.echo("✔ Application spec successfully validated. 🎉")
