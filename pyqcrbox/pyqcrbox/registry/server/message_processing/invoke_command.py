from faststream.rabbit import RabbitBroker

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.helpers import get_routing_key_for_command_invocation_requests

from .base_message_dispatcher import server_side_message_dispatcher


@server_side_message_dispatcher.register
async def handle_command_invocation(msg: msg_specs.InvokeCommand, broker: RabbitBroker, **kwargs):
    assert msg.action == "invoke_command"

    logger.warning("TODO: generate correlation_id here instead of accepting it as part of the incoming message")

    cmd_invocation = msg.payload
    try:
        cmd_invocation_db = cmd_invocation.save_to_db()
    except sql_models.QCrBoxDBError as exc:
        return msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=exc.message)

    correlation_id = cmd_invocation_db.correlation_id
    new_msg = msg_specs.CommandInvocationRequest(
        action="command_invocation_request",
        payload=msg.payload,
    )

    rk_command_invocation_requests = get_routing_key_for_command_invocation_requests(
        application_slug=msg.payload.application_slug,
        application_version=msg.payload.application_version,
    )
    await broker.publish(new_msg, rk_command_invocation_requests)

    # TODO: generate a unique correlation_id here and add it to the response payload

    return msg_specs.responses.ok(
        response_to=msg.action,
        payload={"correlation_id": correlation_id},
    )


@server_side_message_dispatcher.register
async def handle_client_indicating_availability_for_command_execution(
    msg: msg_specs.ClientIndicatesAvailabilityToExecuteCommand, broker: RabbitBroker, **kwargs
):
    assert msg.action == "client_is_available_to_execute_command"
    msg_execute_command = msg_specs.ExecuteCommand(
        action="execute_command",
        payload=sql_models.CommandExecutionCreate(
            application_slug=msg.payload.cmd_invocation_payload.application_slug,
            application_version=msg.payload.cmd_invocation_payload.application_version,
            command_name=msg.payload.cmd_invocation_payload.command_name,
            arguments=msg.payload.cmd_invocation_payload.arguments,
            correlation_id=msg.payload.cmd_invocation_payload.correlation_id,
            private_routing_key=msg.payload.private_routing_key,
        ),
    )
    response = await broker.publish(msg_execute_command, msg.payload.private_routing_key, rpc=True)
    assert response["status"] == msg_specs.ResponseStatusEnum.OK
