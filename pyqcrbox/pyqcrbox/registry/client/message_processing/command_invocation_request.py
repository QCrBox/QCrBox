from pyqcrbox import msg_specs

from .base_message_dispatcher import client_side_message_dispatcher


@client_side_message_dispatcher.register
def handle_command_invocation_request(msg: msg_specs.CommandInvocationRequest, self, **kwargs):
    assert msg.action == "command_invocation_request"
    return msg_specs.responses.error(response_to=msg.action, msg="TODO")
