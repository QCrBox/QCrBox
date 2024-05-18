# SPDX-License-Identifier: MPL-2.0

import sys
from typing import Iterable, Optional

import click
import requests
from dateutil.parser import parse as parse_date
from loguru import logger
from tabulate import tabulate

from pyqcrbox import settings

from ...helpers import get_qcrbox_registry_api_connection_url
from ..helpers import DockerProject, NaturalOrderGroup


def extract_columns(cols_to_print: Iterable[str]):
    def extract_columns_impl(row_dict):
        return {key: row_dict[key] for key in cols_to_print}

    return extract_columns_impl


def pretty_print_timestamp(colname):
    def pretty_print_timestamp_impl(row_dict):
        ts = parse_date(row_dict.pop(colname))
        row_dict[colname] = ts.strftime("%Y-%m-%d %H:%M:%S")
        return row_dict

    return pretty_print_timestamp_impl


def update_status_of_containers():
    logger.debug("Requesting status update of containers in the registry database.")
    qcrbox_api_base_url = get_qcrbox_registry_api_connection_url()
    try:
        r = requests.post(qcrbox_api_base_url + "/containers/status_update")
        return r
    except requests.exceptions.ConnectionError:
        click.echo(f"Error: could not connect to QCrBox registry at {qcrbox_api_base_url}")
        sys.exit(1)


@click.group(name="list", cls=NaturalOrderGroup)
def list_qcrbox_resources():
    """
    List registered resources (applications, commands, etc.)
    """
    pass


def run_request_against_registry_api(endpoint, params):
    try:
        r = requests.get(settings.registry.server.api_url + endpoint, params=params)
        return r
    except requests.exceptions.ConnectionError:
        click.echo(f"Error: could not connect to QCrBox registry at {settings.registry.server.api_url}")
        sys.exit(1)


@list_qcrbox_resources.command(name="components")
@click.option(
    "-a",
    "--all",
    "include_all_components",
    default=False,
    is_flag=True,
    help="List all components (including base images that are only used during the build process)",
)
def list_available_componens(include_all_components):
    """
    List available QCrBox components.

    These can be used as arguments in the commands `qcb build/up/down`.
    """
    docker_project = DockerProject()

    if include_all_components:
        components = docker_project.services_including_base_images
    else:
        components = docker_project.services_excluding_base_images

    for component in components:
        click.echo(component)


@list_qcrbox_resources.command(name="applications")
@click.option(
    "--name",
    default=None,
    help="Filter applications by name (must match exactly)",
)
@click.option(
    "--version",
    default=None,
    help="Filter applications by version (must match exactly)",
)
def list_applications(name: Optional[str], version: Optional[str]):
    """
    List registered applications.
    """
    r = run_request_against_registry_api("/applications", params={"name": name, "version": version})

    cols_to_print = (
        "id",
        "slug",
        "name",
        "version",
        "registered_at",
    )
    data = [pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row)) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="commands")
@click.option(
    "--name",
    default=None,
    help="Filter commands by name (must match exactly)",
)
@click.option(
    "--application-id",
    default=None,
    type=int,
    help="Filter commands by application_id (run 'qcb list applications' to get the id)",
)
def list_commands(name: Optional[str], application_id: Optional[int]):
    """
    List registered commands.
    """
    r = run_request_against_registry_api("/commands", params={"name": name, "application_id": application_id})
    cols_to_print = (
        "id",
        "application_id",
        "name",
        "parameters",
    )
    data = [extract_columns(cols_to_print)(row) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="containers")
@click.option(
    "--application-id",
    default=None,
    type=int,
    help="Filter containers by application_id (run 'qcb list applications' to get the id)",
)
@click.option(
    "--update-status",
    is_flag=True,
    default=False,
    type=bool,
    help=(
        "Ensure the status of all containers in the registry database is up to date before listing them. "
        "This is disabled by default because it currently takes about a second per container "
        "(it will be much faster once proper async support is added)."
    ),
)
def list_containers(application_id: Optional[int], update_status: bool):
    """
    List registered containers.
    """
    if update_status:
        update_status_of_containers()

    r = run_request_against_registry_api("/containers", params={"application_id": application_id})
    cols_to_print = (
        "id",
        "qcrbox_id",
        "registered_at",
        "application_id",
        "status",
    )  # we're dropping column 'routing_key__registry_to_application'
    data = [pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row)) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))
