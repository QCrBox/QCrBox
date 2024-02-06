# SPDX-License-Identifier: MPL-2.0
import shutil
import sys
from pathlib import Path

import click
from cookiecutter.main import cookiecutter as run_cookiecutter
from loguru import logger

from ..helpers import get_repo_root


@click.command(name="init")
@click.option(
    "-t",
    "--application-type",
    required=False,
    default="cli",
    help="Which type of application template should be used. Valid options: 'cli', 'gui-linux', 'gui-windows'",
)
@click.option(
    "-f",
    "--overwrite-if-exists",
    is_flag=True,
    default=False,
    help="Overwrite the contents of the target directory services/applications/<application_slug> if it already exists",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Display actions that would be performed without actually doing anything.",
)
@click.argument(
    "application_slug",
    metavar="<application_slug>",
    # help=(
    #     "The slug is used as the directory name for the new application "
    #     "(as a subfolder of services/applications/) and also as a unique "
    #     "identifier in other contexts."
    # ),
)
def create_application_template(application_type, overwrite_if_exists, dry_run, application_slug):
    """
    Create boilerplate template for a new application.

    The argument <application_slug> should be a short,
    human-readable identifier for the application.

    Among other things, it will be used as the name of the directory where the
    template is created (as a subfolder of 'services/applications/') and can only
    contain lowercase letters and underscores. Example: 'crystal_explorer'
    """
    repo_root = get_repo_root()
    template_dir = str(repo_root.joinpath("services", "applications", "_templates", "cli_application"))
    target_dir = repo_root.joinpath("services", "applications", application_slug)
    if target_dir.exists():
        if overwrite_if_exists:
            logger.info(
                f"Directory {target_dir} already exists. Discarding existing contents "
                f"because --overwrite-if-exists is enabled."
            )
            shutil.rmtree(target_dir)
        elif any(target_dir.iterdir()):
            logger.info(
                f"Directory {target_dir} exists and is not empty. Please specify "
                f"--overwrite-if-exists to discard any existing contents."
            )
            sys.exit()
        else:
            pass
    result_dir = run_cookiecutter(
        template_dir,
        output_dir=target_dir,
        overwrite_if_exists=overwrite_if_exists,
        extra_context={"application_slug": application_slug},
    )
    logger.info(f"Created scaffolding for new application in '{Path(result_dir)}'.")
