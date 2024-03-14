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
    msg: msg_specs.InvokeCommand,
    logger: Logger,
    broker: RabbitBroker = Context("broker"),
) -> msg_specs.InvokeCommandResponse:
    """
    Invoke a command that is implemented by a previously registered application.
    """
    #    cmd = sql_models.CommandInvocationCreate(**msg.payload.model_dump())
    cmd_invocation = sql_models.CommandInvocationCreate(**msg.payload.model_dump())
    cmd_invocation_db = cmd_invocation.save_to_db()
    if cmd_invocation_db.application_id and cmd_invocation_db.command_id:
        response = msg_specs.InvokeCommandResponse(
            response_to=msg.action,
            status="ok",
            msg="Received command invocation request.",
        )
        with settings.db.get_session() as session:
            application = session.exec(
                select(sql_models.ApplicationSpecDB).where(
                    sql_models.ApplicationSpecDB.id == cmd_invocation_db.application_id
                )
            ).one()
            logger.debug(
                f"Sending command invocation request to queue for {application.slug!r}, "
                f"version {application.version!r}"
            )
            await broker.publish(
                cmd_invocation.model_dump(),
                routing_key=application.routing_key_command_invocation,
            )
    else:
        error_msg = (
            f"Error when processing command invocation: could not find an application implementing "
            f"the requested command (correlation_id={cmd_invocation.correlation_id})"
        )
        logger.error(error_msg)
        response = msg_specs.InvokeCommandResponse(
            response_to=msg.action,
            status="error",
            msg=error_msg,
        )

    return response

    #
    # return msg_specs.InvokeCommandResponse(
    #     response_to=msg.action,
    #     status="ok",
    #     msg=f"Successfully registered application {app_db.name!r} (id: {app_db.id})",
    #     payload=msg_specs.RegisterApplicationResponse.Payload(
    #         application_id=assigned_application_id,
    #     ),
    # )
