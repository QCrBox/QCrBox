import time
from uuid import uuid4

from faststream import Logger, apply_types

__all__ = ["generate_correlation_id", "generate_private_routing_key"]


@apply_types
def generate_private_routing_key(logger: Logger):
    result = create_unique_id(prefix="qcrbox_rk_")
    logger.debug(f"Generated private routing key: {result}")
    return result


@apply_types
def generate_correlation_id(logger: Logger):
    result = create_unique_id(prefix="qcrbox_corr_id_")
    logger.debug(f"Generated random correlation id: {result}")
    return result


def create_unique_id(*, prefix=""):
    return f"{prefix}0x{uuid4().hex}"


def print_and_sleep(duration: float = 1.0):
    print("Hello world!")
    time.sleep(duration)
    print("Goodbye.")
    return f"Successfully slept for {duration:.1f} seconds"
