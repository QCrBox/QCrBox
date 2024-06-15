import anyio
from faststream.rabbit import RabbitBroker

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.helpers import get_routing_key_for_command_invocation_requests

from .base_message_dispatcher import server_side_message_dispatcher


def create_invocation_notification_handler(self, correlation_id: str):
    logger.debug(f"Creating new command execution event for calculation with {correlation_id=}")
    event = anyio.Event()
    self._notification_events[correlation_id] = event

    async def notification_handler():
        await event.wait()
        logger.debug(
            f"Received a client response to invocation request for calculation with {correlation_id=}"
            "Request for command execution will have been sent to this client."
        )

    return notification_handler


@server_side_message_dispatcher.register
async def handle_command_invocation(msg: msg_specs.InvokeCommand, self, broker: RabbitBroker, **kwargs):
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

    invocation_signal_handler = create_invocation_notification_handler(self, msg.payload.correlation_id)
    routing_key_cmd_invocation_requests = get_routing_key_for_command_invocation_requests(
        application_slug=msg.payload.application_slug,
        application_version=msg.payload.application_version,
    )

    async with anyio.create_task_group() as tg:
        logger.info("Sending command invocation request to available clients.")
        tg.start_soon(invocation_signal_handler)
        tg.start_soon(broker.publish, new_msg, routing_key_cmd_invocation_requests)

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
