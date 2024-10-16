# from faststream.rabbit import RabbitBroker
# from .base_message_dispatcher import client_side_message_dispatcher


# async def handle_command_invocation_request_via_nats(msg: msg_specs.CommandInvocationRequest, nats_broker: Context("broker")):
#     assert msg.action == "command_invocation_request"
#     logger.debug(f"Received command invocation request: {msg}")
#
#     msg_indicate_availability = msg_specs.ClientIndicatesAvailabilityToExecuteCommand(
#         action="client_is_available_to_execute_command",
#         payload=msg_specs.PayloadForClientIsAvailableToExecuteCommand(
#             cmd_invocation_payload=msg.payload,
#             # private_routing_key=self.private_routing_key,
#         ),
#     )
#
#     server_response = await nats_broker.publish(
#         msg_indicate_availability, f"cmd-invocation.response.{msg.payload.correlation_id}"
#     )
#     logger.debug(f"Received response from server: {server_response}")
#
