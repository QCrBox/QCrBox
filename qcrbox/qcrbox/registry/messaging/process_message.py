from functools import singledispatch
from ...logging import logger


@singledispatch
def process_message(msg):
    """
    Fallback processing definition, in case none of the others match.
    """
    logger.warning("TODO: add a more informative error message here (and return a proper QCrBoxGenericResponse)!")
    raise NotImplementedError(f"Cannot process incoming message: {msg}")
