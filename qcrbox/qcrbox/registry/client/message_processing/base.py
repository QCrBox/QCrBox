# SPDX-License-Identifier: MPL-2.0

import asyncio
from functools import singledispatch

from loguru import logger

from qcrbox.common import msg_specs


async def process_message_sync_or_async(msg, application):
    """
    Wrapper function which allows to define both sync and async implementations of `process_message`.
    """
    logger.debug("[DDD] Processing message ...")
    result = process_message(msg, application)
    logger.debug("[DDD] Done processing message.")
    if asyncio.iscoroutine(result):
        # If the given message type is processed by an async function,
        # calling `process_message` will return a coroutine, so we need
        # to await this in order to retrieve the actual result.
        result = await result
    return result


@singledispatch
async def process_message(msg, application):
    """
    Fallback processing definition, in case none of the others match.
    """
    error_msg = f"No matching handler found for incoming message: {msg}"
    logger.error(error_msg)
    return msg_specs.QCrBoxGenericResponse(response_to="incoming_message", status="error", msg=error_msg)
