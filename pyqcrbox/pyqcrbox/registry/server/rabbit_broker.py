import inspect
import json

import pydantic
from faststream.rabbit import RabbitBroker
from loguru import logger

from pyqcrbox import msg_specs, settings
from pyqcrbox.msg_specs import InvalidQCrBoxAction, look_up_action_class

from .message_processing import process_message_dispatcher

__all__ = ["set_up_server_rabbitmq_broker"]


async def process_message_server_side(msg: dict):
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

    result = process_message_dispatcher(msg_obj)
    if inspect.iscoroutine(result):
        # If the given message type is processed by an async function,
        # calling `process_message` will return a coroutine, so we need
        # to await this in order to retrieve the actual result.
        result = await result
    return result


def set_up_server_rabbitmq_broker(broker: RabbitBroker) -> None:
    # Note: usually `@broker.subscriber(...)` is used as a decorator,
    #       but here we call it directly with `process_message_NEW`
    #       as an argument, which will register this function as a
    #       handler for incoming messages.
    broker.subscriber(settings.rabbitmq.routing_key_qcrbox_registry)(process_message_server_side)
