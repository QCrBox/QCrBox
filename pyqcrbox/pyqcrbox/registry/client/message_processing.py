import functools
import textwrap

from pyqcrbox import logger, msg_specs


@functools.singledispatch
def client_side_message_dispatcher(msg: dict):
    """
    Fallback processing definition.

    This is executed only if none of the other registered handlers match.
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


@client_side_message_dispatcher.register
def health_check(msg: msg_specs.HealthCheck):
    assert msg.action == "health_check"
    return msg_specs.responses.health_check_healthy()