from pyqcrbox import msg_specs

from .base_message_dispatcher import client_side_message_dispatcher


@client_side_message_dispatcher.register
def health_check(msg: msg_specs.HealthCheck, **kwargs):
    assert msg.action == "health_check"
    return msg_specs.responses.health_check_healthy()
