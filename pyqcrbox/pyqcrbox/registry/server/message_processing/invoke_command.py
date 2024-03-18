# SPDX-License-Identifier: MPL-2.0
import sqlalchemy
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
    cmd_invocation = msg.payload
    try:
        cmd_invocation_db = cmd_invocation.save_to_db()
    except sqlalchemy.exc.IntegrityError as exc:
        exception_msg = exc._message()
        if "UNIQUE constraint failed: command_invocation.correlation_id" in exception_msg:
            error_msg = (
                f"correlation_id must be unique for each command invocation, "
                f"but found existing value: {cmd_invocation.correlation_id!r}"
            )
        else:
            error_msg = f"Internal server error (original error message: {exception_msg})"

        response = msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=error_msg)
        return response

    if cmd_invocation_db.application_id is None:
        error_msg = (
            f"The requested application is not available: {cmd_invocation.application_slug!r} "
            f"(version: {cmd_invocation.application_version!r})"
        )
        logger.error(error_msg)
        response = msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=error_msg)
    elif cmd_invocation_db.command_id is None:
        error_msg = (
            f"Application {cmd_invocation.application_slug!r} (version: {cmd_invocation.application_version!r} "
            f"does not implement the requested command: {cmd_invocation.command_name!r}"
        )
        logger.error(error_msg)
        response = msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=error_msg)
    else:
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
