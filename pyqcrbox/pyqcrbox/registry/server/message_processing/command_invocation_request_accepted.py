# SPDX-License-Identifier: MPL-2.0
from faststream import Context, Logger, apply_types
from faststream.rabbit import RabbitBroker
from sqlmodel import select

from pyqcrbox import msg_specs, settings, sql_models
from pyqcrbox.msg_specs import process_message

__all__ = []


@process_message.register
@apply_types
async def _(
    msg: msg_specs.CommandInvocationRequestAccepted,
    logger: Logger,
    broker: RabbitBroker = Context("broker"),
) -> None:
    """
    command_invocation_request_accepted
      - from: client
      - to: server
      - rpc: no
    """
    logger.debug(f"Application accepted command invocation with correlation_id={msg.payload.correlation_id}")

    with settings.db.get_session() as session:
        cmd_invocation_db = session.exec(
            select(sql_models.CommandInvocationDB).where(
                sql_models.CommandInvocationDB.correlation_id == msg.payload.correlation_id
            )
        ).one()
        cmd_spec_db = cmd_invocation_db.command

    logger.debug("Sending command execution request to this application.")
    msg_execute_cmd = msg_specs.InitiateCommandExecution(
        action="initiate_command_execution",
        payload=msg_specs.PayloadForInitiateCommandExecution(
            command_invocation_db=cmd_invocation_db,
            command_spec_db=cmd_spec_db,
        ),
    )
    await broker.publish(msg_execute_cmd, routing_key=msg.payload.private_routing_key)
