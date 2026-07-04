# SPDX-License-Identifier: MPL-2.0

import sys
from collections.abc import Iterable

import click
import requests
from dateutil.parser import parse as parse_date
from tabulate import tabulate

from pyqcrbox import settings

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


@click.group(name="list", cls=NaturalOrderGroup)
def list_qcrbox_resources():
    """List registered resources (applications, commands, etc.)."""


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
def list_available_components(include_all_components):
    """
    List available QCrBox components.

    These can be used as arguments in `qcb build/up/down`.
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
    "--slug",
    default=None,
    help="Filter applications by slug (must match exactly)",
)
@click.option(
    "--version",
    default=None,
    help="Filter applications by version (must match exactly)",
)
def list_applications(slug: str | None, version: str | None):
    """List registered applications."""
    r = run_request_against_registry_api("/applications", params={"slug": slug, "version": version})

    cols_to_print = (
        "id",
        "slug",
        "name",
        "version",
        "registered_at",
    )
    data = [
        pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row))
        for row in r.json()["payload"]["applications"]
    ]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="commands")
@click.option(
    "--name",
    default=None,
    help="Filter commands by name (must match exactly)",
)
@click.option(
    "--application-slug",
    default=None,
    type=str,
    help="Filter commands by application_slug (run 'qcb list applications' to get the slug)",
)
@click.option(
    "--application-version",
    default=None,
    type=str,
    help="Filter commands by application_version (run 'qcb list applications' to get the version)",
)
@click.option(
    "-a",
    "--all",
    "include_interactive_lifecycle_steps",
    is_flag=True,
    default=False,
    help="List all commands (including interactive lifecycle steps)",
)
def list_commands(
    name: str | None,
    application_slug: str | None,
    application_version: str | None,
    include_interactive_lifecycle_steps: bool,
):
    """List registered commands."""
    r = run_request_against_registry_api(
        "/commands",
        params={"name": name, "application_slug": application_slug, "application_version": application_version},
    )
    assert r.status_code == 200, "Error retrieving commands from server"
    cols_to_print = (
        # "id",
        "application",
        "version",
        "cmd_name",
        "parameters",
    )
    data = [
        extract_columns(cols_to_print)(row)
        for row in r.json()["payload"]["commands"]
        if not row["name"].startswith("__interactive_") or include_interactive_lifecycle_steps
    ]
    for row in data:
        row["parameters"] = list(row["parameters"].keys())
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="containers")
@click.option(
    "--slug",
    default=None,
    help="Filter container instances by application slug (must match exactly)",
)
@click.option(
    "--version",
    default=None,
    help="Filter container instances by application version (must match exactly)",
)
def list_containers(slug: str | None, version: str | None):
    """List tracked container instances (live application containers)."""
    r = run_request_against_registry_api("/container-instances", params={"slug": slug, "version": version})
    assert r.status_code == 200, "Error retrieving container instances from server"
    cols_to_print = (
        "id",
        "client_id",
        "application_slug",
        "application_version",
        "status",
        "last_seen",
    )
    data = [
        pretty_print_timestamp("last_seen")(extract_columns(cols_to_print)(row))
        for row in r.json()["payload"]["container_instances"]
    ]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="calculations")
def list_calculations():
    """List calculations."""
    r = run_request_against_registry_api("/calculations", params={})
    assert r.status_code == 200, "Error retrieving calculations from server"
    cols_to_print = (
        "calculation_id",
        "application_slug",
        "application_version",
        "status",
        "command_name",
        "command_arguments",
    )
    data = [extract_columns(cols_to_print)(row) for row in r.json()["payload"]["calculations"]]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))
