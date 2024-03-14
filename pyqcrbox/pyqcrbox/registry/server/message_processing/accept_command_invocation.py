# SPDX-License-Identifier: MPL-2.0
from faststream import Context, Logger, apply_types
from faststream.rabbit import RabbitBroker
from sqlmodel import select

from pyqcrbox import msg_specs, settings, sql_models

from .base import process_message

__all__ = []


@process_message.register
@apply_types
async def _(
    msg: msg_specs.AcceptCommandInvocation,
    logger: Logger,
    broker: RabbitBroker = Context("broker"),
) -> None:
    """
    Send command execution command to the application who accepted the command invocation request.
    """
    logger.debug(f"Application accepted command invocation with correlation_id={msg.payload.correlation_id}")

    with settings.db.get_session() as session:
        cmd_invocation_db = session.exec(
            select(sql_models.CommandInvocationDB).where(
                sql_models.CommandInvocationDB.correlation_id == msg.payload.correlation_id
            )
        ).one()

    logger.debug("Sending command execution request to this application.")
    msg_execute_cmd = msg_specs.InitiateCommandExecution(
        action="initiate_command_execution",
        payload=msg_specs.PayloadForInitiateCommandExecution(
            command_invocation_db=cmd_invocation_db,
        ),
    )
    await broker.publish(msg_execute_cmd, routing_key=msg.payload.private_routing_key)
