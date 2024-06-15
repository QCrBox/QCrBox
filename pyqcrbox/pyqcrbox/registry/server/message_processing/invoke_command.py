from faststream.rabbit import RabbitBroker

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.helpers import get_routing_key_for_command_invocation_requests

from .base_message_dispatcher import server_side_message_dispatcher


@server_side_message_dispatcher.register
async def handle_command_invocation(msg: msg_specs.InvokeCommand, broker: RabbitBroker, **kwargs):
    assert msg.action == "invoke_command"

    logger.warning("TODO: generate correlation_id here instead of accepting it as part of the incoming message")

    calculation_db = sql_models.CalculationDB(
        application_slug=msg.payload.application_slug,
        application_version=msg.payload.application_version,
        command_name=msg.payload.command_name,
        arguments=msg.payload.arguments,
        correlation_id=msg.payload.correlation_id,  # FIXME: generate this here (see TODO comment above)
    )
    try:
        calculation_db.save_to_db()
    except sql_models.QCrBoxDBError as exc:
        return msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=exc.message)

    new_msg = msg_specs.CommandInvocationRequest(
        action="command_invocation_request",
        payload=msg.payload,
    )

    rk_command_invocation_requests = get_routing_key_for_command_invocation_requests(
        application_slug=msg.payload.application_slug,
        application_version=msg.payload.application_version,
    )
    await broker.publish(new_msg, rk_command_invocation_requests)

    try:
        calculation_db.update_status(sql_models.CalculationStatusEnum.CHECKING_CLIENT_AVAILABILITY)
        calculation_db.save_to_db()
    except sql_models.QCrBoxDBError as exc:
        return msg_specs.InvokeCommandResponse(response_to=msg.action, status="error", msg=exc.message)

    return msg_specs.responses.ok(
        response_to=msg.action,
        payload={
            "calculation_id": calculation_db.id,
            "correlation_id": calculation_db.correlation_id,
        },
    )


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
