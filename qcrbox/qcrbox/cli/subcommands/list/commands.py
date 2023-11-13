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
    Print a list of resources of a given kind, e.g., applications/commands/containers/calculations.
    """
    pass


@print_list_of_resources.command(name="applications")
def list_applications():
    """
    Print a list of registered applications.
    """
    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/applications")
    data = [pretty_print_timestamp("registered_at")(row) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@print_list_of_resources.command(name="commands")
def list_commands():
    """
    Print a list of registered commands.
    """
    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/commands")
    data = [row for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))


@print_list_of_resources.command(name="containers")
def list_containers():
    """
    Print a list of registered containers.
    """
    # We're dropping column 'routing_key__registry_to_application'
    cols_to_print = ("id", "qcrbox_id", "registered_at", "application_id", "status")

    qcrbox_api_base_url = get_qcrbox_api_base_url()
    r = requests.get(qcrbox_api_base_url + "/containers")
    data = [pretty_print_timestamp("registered_at")(extract_columns(cols_to_print)(row)) for row in r.json()]
    click.echo(tabulate(data, headers="keys", tablefmt="simple"))
