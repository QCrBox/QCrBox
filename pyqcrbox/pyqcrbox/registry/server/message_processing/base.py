# SPDX-License-Identifier: MPL-2.0

import asyncio
from functools import singledispatch

from loguru import logger  # TODO: switch to FastStream logger

from pyqcrbox.msg_specs import QCrBoxGenericResponse


async def process_message_sync_or_async(msg):
    """
    Wrapper function which allows to define both sync and async implementations of `process_message`.
    """
    result = process_message(msg)
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
