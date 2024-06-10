from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs, sql_models
from pyqcrbox.helpers import ensure_dict, get_routing_key_for_command_invocation_requests

from .base_message_dispatcher import server_side_message_dispatcher


@server_side_message_dispatcher.register
async def handle_command_invocation(msg: msg_specs.InvokeCommand, broker: RabbitBroker, **kwargs):
    assert msg.action == "invoke_command"

    new_msg = msg_specs.CommandInvocationRequest(
        action="command_invocation_request",
        payload=msg.payload,
    )

    rk_command_invocation_requests = get_routing_key_for_command_invocation_requests(
        application_slug=msg.payload.application_slug,
        application_version=msg.payload.application_version,
    )
    await broker.publish(new_msg, rk_command_invocation_requests)


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
    response = ensure_dict(
        response
    )  # TODO: delete me when this is fixed: https://github.com/airtai/faststream/issues/1437
    assert response["status"] == msg_specs.ResponseStatusEnum.OK
