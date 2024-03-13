# SPDX-License-Identifier: MPL-2.0
from faststream import Context, Logger, apply_types
from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, sql_models

from .base import process_message

__all__ = []


@process_message.register
@apply_types
async def _(
    msg: msg_specs.AcceptCommandInvocation,
    logger: Logger,
    broker: RabbitBroker = Context("broker"),
) -> msg_specs.AcceptCommandInvocationResponse:
    """
    Send command execution command to the application who accepted the command invocation request.
    """
    logger.debug(f"Application accepted command invocation with correlation_id={msg.payload.correlation_id}")
    logger.debug("Sending command execution request to this application.")
    msg_execute_cmd = msg_specs.ExecuteCommand(
        action="execute_command",
        payload=sql_models.CommandInvocationCreate(**msg.payload.model_dump(exclude={"private_routing_key"})),
    )
    await broker.publish(msg_execute_cmd, routing_key=msg.payload.private_routing_key)

    response = msg_specs.AcceptCommandInvocationResponse(
        response_to=msg.action,
        status="success",
        msg="Submitted command execution request to client application.",
        payload=msg_specs.AcceptCommandInvocation.Payload(**msg.payload.model_dump()),
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
