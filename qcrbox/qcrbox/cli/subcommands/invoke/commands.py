import json
from typing import Optional

import click
import requests

from ....logging import logger
from ....registry import msg_specs
from ....registry.helpers import get_qcrbox_registry_api_connection_url


@click.command(name="invoke")
@click.option("--command-id", type=int, required=True, help="Id of the command to be invoked.")
@click.option(
    "--with-args",
    type=str,
    default=None,
    help="JSON representation of the command arguments (run 'qcb list commands' to get details)",
)
def invoke_command(command_id: int, with_args: Optional[str] = None):
    """
    Invoke a registered command with given arguments.
    """
    qcrbox_api_base_url = get_qcrbox_registry_api_connection_url()

    with_args = json.loads(with_args) or dict()
    logger.debug(f"[DDD] {with_args=} ({type(with_args)=})")
    logger.warning(
        f"FIXME: provide feedback on whether the arguments were provided correctly "
        f"(currently the command just fails to run silently within the container)"
    )

    payload = msg_specs.InvokeCommand(
        action="invoke_command",
        payload=msg_specs.QCrBoxCalculationCreate(
            command_id=command_id,
            arguments=with_args,
        ),
    )
    click.echo("Sending command invocation request to QCrBox")
    r = requests.post(qcrbox_api_base_url + "/invoke_command", json=payload.dict())
    # breakpoint()
    click.echo(f"{r=}")
    click.echo(r.json())
    pass
