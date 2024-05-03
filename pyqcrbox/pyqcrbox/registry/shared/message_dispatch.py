import inspect
import json
from typing import Callable

import pydantic
from faststream.rabbit import RabbitBroker
from loguru import logger

from pyqcrbox import msg_specs
from pyqcrbox.msg_specs import (
    InvalidQCrBoxAction,
    InvalidQCrBoxResponse,
    QCrBoxBaseMessage,
    look_up_action_class,
    look_up_response_class,
)

__all__ = ["declare_rabbitmq_message_handler"]


def declare_rabbitmq_message_handler(
    self,
    broker: RabbitBroker,
    *,
    routing_key: str,
    msg_dispatcher_func: Callable,
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
    async def process_message(msg: dict) -> QCrBoxBaseMessage | None:
        """
        Wrapper function which allows to define both sync and async implementations of `process_message`.
        """

        def log_error_msg_and_create_response(error_msg: str):
            logger.error(error_msg)
            return msg_specs.responses.error(response_to="incoming_message", msg=error_msg)

        if isinstance(msg, (str, bytes)):
            try:
                msg = json.loads(msg)
            except Exception as exc:
                return log_error_msg_and_create_response(
                    f"Incoming message does not represent a valid JSON structure: {msg}.\nThe original error was: {exc}"
                )

        if "action" in msg:
            try:
                action_cls = look_up_action_class(msg["action"])
            except InvalidQCrBoxAction:
                error_msg = f"Invalid action: {msg['action']!r}"
                return log_error_msg_and_create_response(error_msg)

            try:
                msg_obj = action_cls(**msg)
            except pydantic.ValidationError as exc:
                error_msg = f"Invalid message structure for action {msg['action']!r}. Errors: {exc.errors()}"
                return log_error_msg_and_create_response(error_msg)
        elif "response_to" in msg:
            try:
                response_cls = look_up_response_class(msg["response_to"])
            except InvalidQCrBoxResponse:
                logger.trace(f"No explicit handler defined for response type: {msg['response_to']}")
                # TODO: return at least some kind of valid QCrBox message instead of None
                #       (also remove 'None' from the return type annotation above)
                return None

            try:
                msg_obj = response_cls(**msg)
            except pydantic.ValidationError as exc:
                error_msg = f"Invalid message structure for response {msg['response_to']!r}. Errors: {exc.errors()}"
                return log_error_msg_and_create_response(error_msg)
        else:
            error_msg = "Invalid message structure: message must have an 'action' or 'response_to' field"
            return log_error_msg_and_create_response(error_msg)

        result = msg_dispatcher_func(msg_obj, self=self, broker=broker)

        if inspect.iscoroutine(result):
            # If the given message type is processed by an async function,
            # calling `process_message` will return a coroutine, so we need
            # to await this in order to retrieve the actual result.
            result = await result
        return result

    return process_message
