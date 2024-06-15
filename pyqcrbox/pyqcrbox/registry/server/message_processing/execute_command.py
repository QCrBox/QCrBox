from faststream.rabbit import RabbitBroker

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.registry.server.message_processing import server_side_message_dispatcher


@server_side_message_dispatcher.register
async def handle_client_indicating_availability_for_command_execution(
    msg: msg_specs.ClientIndicatesAvailabilityToExecuteCommand, broker: RabbitBroker, **kwargs
):
    assert msg.action == "client_is_available_to_execute_command"

    logger.debug(
        "Received message from client indicating availability to execute command: "
        f"correlation_id={msg.payload.cmd_invocation_payload.correlation_id}, "
        f"{msg.payload.private_routing_key=}"
    )

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
    response_dict = await broker.publish(
        msg_execute_command, msg.payload.private_routing_key, rpc=True, raise_timeout=True
    )
    logger.debug(f"Received response from client: {response_dict}")
    response = msg_specs.QCrBoxGenericResponse(**response_dict)
    return response
