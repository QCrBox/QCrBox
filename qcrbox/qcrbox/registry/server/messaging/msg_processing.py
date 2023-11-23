import asyncio
from functools import singledispatch

from ....logging import logger


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
    Fallback processing definition, in case none of the others match.
    """
    logger.warning("TODO: add a more informative error message here (and return a proper QCrBoxGenericResponse)!")
    raise NotImplementedError(f"Cannot process incoming message: {msg}")
