import sys
from typing import Optional, Iterable

import click
import requests
from dateutil.parser import parse as parse_date
from tabulate import tabulate

from ....registry.helpers import get_qcrbox_registry_api_connection_url


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


@click.group(name="list")
def list_qcrbox_resources():
    """
    List registered resources (applications, commands, etc.)
    """
    pass


def run_request_against_registry_api(endpoint, params):
    qcrbox_api_base_url = get_qcrbox_registry_api_connection_url()
    try:
        r = requests.get(qcrbox_api_base_url + endpoint, params=params)
        return r
    except requests.exceptions.ConnectionError:
        click.echo(f"Error: could not connect to QCrBox registry at {qcrbox_api_base_url}")
        sys.exit(1)


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
    data = [pretty_print_timestamp("registered_at")(row) for row in r.json()]
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
    data = [row for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@list_qcrbox_resources.command(name="containers")
@click.option(
    "--application-id",
    default=None,
    type=int,
    help="Filter containers by application_id (run 'qcb list applications' to get the id)",
)
def list_containers(application_id: Optional[int]):
    """
    List registered containers.
    """
    # We're dropping column 'routing_key__registry_to_application'
    r = run_request_against_registry_api("/containers", params={"application_id": application_id})
    cols_to_print = ("id", "qcrbox_id", "registered_at", "application_id", "status")
    data = [pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row)) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))
