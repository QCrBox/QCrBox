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
    logger.debug(f"Application accepted command invocation with correlation_id={msg.payload.correlation_id!r}")

    with settings.db.get_session() as session:
        cmd_invocation_db = session.exec(
            select(sql_models.CommandInvocationDB).where(
                sql_models.CommandInvocationDB.correlation_id == msg.payload.correlation_id
            )
        ).one()

        cmd_execution = sql_models.CommandExecutionCreate(
            private_routing_key=msg.payload.private_routing_key,
            **cmd_invocation_db.model_dump(
                exclude={"id", "timestamp", "application_id", "command_id", "command_execution_id"}
            ),
        )
        cmd_execution_db = cmd_execution.save_to_db()

        # Link up existing command invocation record with the new command execution record
        cmd_invocation_db.command_execution_id = cmd_execution_db.id
        session.commit()

    logger.debug("Sending command execution request to this application.")
    msg_execute_cmd = msg_specs.ExecuteCommand(action="execute_command", payload=cmd_execution)

    await broker.publish(msg_execute_cmd, routing_key=msg.payload.private_routing_key)
