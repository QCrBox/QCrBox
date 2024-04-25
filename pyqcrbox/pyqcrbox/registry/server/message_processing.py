import functools
import textwrap

from pyqcrbox import logger, msg_specs


@functools.singledispatch
def process_message_dispatcher(msg: dict):
    """
    Fallback processing definition (this is executed only if none of the others match).
    """
    error_msg = textwrap.dedent(
        f"""
        Cannot process incoming message: {msg}.

        If it represents an action, make sure that:

        (1) there exists a submodule of `pyqcrbox.msg_specs.msg_types` which defines
        a subclass of QCrBoxBaseAction associated with this action (and this submodule
        is imported in `pyqcrbox/msg_specs/msg_types/__init__.py`)

        (2) there exists a submodule of `pyqcrbox.registry.{{server|client}}.message_processing`
        which defines a handler for this action (and this submodule is imported in
        `pyqcrbox/registry/{{server|client}}/message_processing/__init__.py
        """
    )
    logger.warning(error_msg)
    return msg_specs.responses.error(response_to="incoming_message", msg=error_msg)


# @process_message_dispatcher.register
def handle_application_registration_request(msg: msg_specs.RegisterApplication):
    assert msg.action == "register_application"
    response_msg = msg_specs.responses.success(response_to=msg.action)
    # broker.publish(response_msg, msg.payload.private_routing_key)
    return response_msg


# @process_message_dispatcher.register
def ping_handler(msg: msg_specs.QCrBoxBaseAction):
    assert msg.action == "ping"
    logger.info("[DDD] Handling 'ping' message")
    return msg_specs.responses.success(response_to=msg.action)
