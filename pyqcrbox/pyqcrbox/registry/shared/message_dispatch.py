import inspect
import json
from typing import Callable

import pydantic
from faststream.rabbit import RabbitBroker
from loguru import logger

from pyqcrbox import msg_specs
from pyqcrbox.msg_specs import InvalidQCrBoxAction, look_up_action_class

__all__ = ["declare_rabbitmq_message_handler"]


def declare_rabbitmq_message_handler(
    broker: RabbitBroker, *, routing_key: str, msg_dispatcher_func: Callable
) -> Callable:
    """
    This helper function takes the input argument `msg_dispatcher_func`, warps it
    with some generic validation code, and declares it as a message handler for
    incoming action messages on the given RabbitMQ broker.

    Parameters
    ----------
    msg_dispatcher_func: Callable
        The message dispatcher to be wrapped. This must be a callable that has
        been decorated with `@functools.singledispatch`

    Returns
    -------
    Callable

    """

    @broker.subscriber(routing_key)
    async def process_message(msg: dict):
        """
        Wrapper function which allows to define both sync and async implementations of `process_message`.
        """

        if isinstance(msg, (str, bytes)):
            try:
                msg = json.loads(msg)
            except Exception as exc:
                error_msg = (
                    f"Incoming message does not represent a valid JSON structure: {msg}.\nThe original error was: {exc}"
                )
                logger.error(error_msg)
                return msg_specs.QCrBoxGenericResponse(
                    response_to="incoming_message", status="error", msg=error_msg, payload=None
                )

        if "action" not in msg:
            error_msg = "Invalid message structure: message must have an 'action' field"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        try:
            action_cls = look_up_action_class(msg["action"])
        except InvalidQCrBoxAction:
            error_msg = f"Invalid action: {msg['action']!r}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        try:
            msg_obj = action_cls(**msg)
        except pydantic.ValidationError as exc:
            error_msg = f"Invalid message structure for action {msg['action']!r}. Errors: {exc.errors()}"
            logger.error(error_msg)
            return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)

        result = msg_dispatcher_func(msg_obj)
        if inspect.iscoroutine(result):
            # If the given message type is processed by an async function,
            # calling `process_message` will return a coroutine, so we need
            # to await this in order to retrieve the actual result.
            result = await result
        return result

    return process_message
