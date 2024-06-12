from pyqcrbox import logger, msg_specs

from .base_message_dispatcher import client_side_message_dispatcher


@client_side_message_dispatcher.register
async def handle_execute_command(msg: msg_specs.ExecuteCommand, *, self, **kwargs):
    assert msg.action == "execute_command"

    cmd = self.get_executable_command(msg.payload.command_name)
    calc = await cmd.execute_in_background(**msg.payload.arguments)

    response_msg = f"Started execution of command {msg.payload.command_name!r} ({calc=})"
    logger.debug(response_msg)

    return msg_specs.responses.ok(response_to=msg.action, msg=response_msg)
