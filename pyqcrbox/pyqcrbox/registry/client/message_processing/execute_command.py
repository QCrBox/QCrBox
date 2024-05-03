from pyqcrbox import msg_specs

from .base_message_dispatcher import client_side_message_dispatcher


@client_side_message_dispatcher.register
async def handle_execute_command(msg: msg_specs.ExecuteCommand, *, self, **kwargs):
    assert msg.action == "execute_command"
    response = msg_specs.responses.ok(response_to=msg.action, msg="Command received, getting ready for execution")
    return response
