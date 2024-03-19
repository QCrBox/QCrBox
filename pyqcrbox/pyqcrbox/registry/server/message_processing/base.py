# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
from functools import singledispatch

import pydantic
from loguru import logger  # TODO: switch to FastStream logger

from pyqcrbox import msg_specs
from pyqcrbox.msg_specs import InvalidQCrBoxAction, QCrBoxGenericResponse, look_up_action_class


async def process_message_sync_or_async(msg: dict, msg_processing_func: callable):
    """
    Wrapper function which allows to define both sync and async implementations of `process_message`.
    """

    if isinstance(msg, (str, bytes)):
        try:
            msg = json.loads(msg)
        except Exception as exc:
            error_msg = (
                f"Incoming message does not represent a valid JSON structure: {msg}.\n" f"The original error was: {exc}"
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

    result = msg_processing_func(msg_obj)
    if asyncio.iscoroutine(result):
        # If the given message type is processed by an async function,
        # calling `process_message` will return a coroutine, so we need
        # to await this in order to retrieve the actual result.
        result = await result
    return result


@singledispatch
def process_message(msg):
    """
    Fallback processing definition (this is executed only if none of the others match).
    """
    error_msg = (
        "Cannot process incoming message. If it represents an action, make sure that: "
        "(1) there exists a submodule of `pyqcrbox.msg_specs.actions` which defines a "
        "subclass of QCrBoxBaseAction associated with this action (and this submodule "
        "is imported in `pyqcrbox/msg_specs/actions/__init__.py`), (2) there exists a "
        "submodule of `pyqcrbox.registry.server.message_processing` which defines a "
        "handler for this action (and this submodule is imported in "
        "`pyqcrbox/registry/server/message_processing/__init__.py"
    )
    logger.warning(error_msg)
    return QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)
