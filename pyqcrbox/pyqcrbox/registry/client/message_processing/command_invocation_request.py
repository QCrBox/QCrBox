# from faststream.rabbit import RabbitBroker

from pyqcrbox import logger, msg_specs

# from .base_message_dispatcher import client_side_message_dispatcher


# @client_side_message_dispatcher.register
# async def handle_command_invocation_request(
#     msg: msg_specs.CommandInvocationRequest, *, self, broker: RabbitBroker, **kwargs
# ):
#     assert msg.action == "command_invocation_request"
#     msg_indicate_availability = msg_specs.ClientIndicatesAvailabilityToExecuteCommand(
#         action="client_is_available_to_execute_command",
#         payload=msg_specs.PayloadForClientIsAvailableToExecuteCommand(
#             cmd_invocation_payload=msg.payload,
#             private_routing_key=self.private_routing_key,
#         ),
#     )
#     await broker.publish(msg_indicate_availability, settings.rabbitmq.routing_key_qcrbox_registry)


async def handle_command_invocation_request_via_nats(msg: msg_specs.CommandInvocationRequest):
    assert msg.action == "command_invocation_request"
    logger.debug(f"Received command invocation request: {msg}")

    msg_indicate_availability = msg_specs.ClientIndicatesAvailabilityToExecuteCommand(
        action="client_is_available_to_execute_command",
        payload=msg_specs.PayloadForClientIsAvailableToExecuteCommand(
            cmd_invocation_payload=msg.payload,
            # private_routing_key=self.private_routing_key,
        ),
    )
    return msg_indicate_availability
