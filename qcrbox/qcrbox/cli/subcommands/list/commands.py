from typing import Optional, Iterable

import click
import requests
from dateutil.parser import parse as parse_date
from tabulate import tabulate

from ...helpers import get_qcrbox_api_base_url


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
def print_list_of_resources():
    """
    List registered resources (applications, commands, etc.)
    """
    pass


@print_list_of_resources.command(name="applications")
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
    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/applications", params={"name": name, "version": version})
    data = [pretty_print_timestamp("registered_at")(row) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@print_list_of_resources.command(name="commands")
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
    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/commands", params={"name": name, "application_id": application_id})
    data = [row for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@print_list_of_resources.command(name="containers")
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
    cols_to_print = ("id", "qcrbox_id", "registered_at", "application_id", "status")

    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/containers", params={"application_id": application_id})
    data = [pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row)) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))
