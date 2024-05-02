from faststream.rabbit import RabbitBroker

from pyqcrbox import msg_specs
from pyqcrbox.helpers import get_routing_key_for_command_invocation_requests

from .base_message_dispatcher import server_side_message_dispatcher


@server_side_message_dispatcher.register
async def handle_command_invocation(msg: msg_specs.InvokeCommand, broker: RabbitBroker):
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
