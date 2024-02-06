# SPDX-License-Identifier: MPL-2.0
import sys
from pathlib import Path

import click
from cookiecutter.main import cookiecutter as run_cookiecutter

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
    if target_dir.exists() and any(target_dir.iterdir()) and not overwrite_if_exists:
        print(f"The directory {target_dir} exists and is not empty.")
        print("Please use the flag -f/--overwrite-if-exists to discard any existing contents. ")
        print("Try 'qcb init -h' for further help.")
        sys.exit()

    print("Please provide some basic information about your application.")
    print("The following dialog will guide you through the relevant settings.")
    print()
    # print("At the end you will be able to confirm your choices or abort the ")
    # print("process before any files are created.")
    # print()

    if target_dir.exists():
        if overwrite_if_exists:
            print(f"Note: The directory {target_dir}")
            print("      exists but --overwrite-if-exists is enabled, so existing contents will be discarded.")
            print()
        else:
            # The directory exists but is empty. Remove it before creating
            # the template, otherwise cookiecutter will complain.
            target_dir.rmdir()

    result_dir = run_cookiecutter(
        template_dir,
        output_dir=target_dir.parent,
        overwrite_if_exists=overwrite_if_exists,
        extra_context={"application_slug": application_slug},
    )
    print()
    print(f"Created scaffolding for new application in '{Path(result_dir)}'.")
