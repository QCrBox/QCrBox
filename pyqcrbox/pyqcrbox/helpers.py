import os
import time
from typing import Optional
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


def get_rabbitmq_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    host = host or os.environ.get("QCRBOX_RABBITMQ_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_RABBITMQ_PORT", 5672))
    username = username or os.environ.get("QCRBOX_RABBITMQ_USERNAME", "guest")
    password = password or os.environ.get("QCRBOX_RABBITMQ_PASSWORD", "guest")
    url = f"amqp://{username}:{password}@{host}:{port}/"
    return url


def get_qcrbox_registry_api_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
):
    host = host or os.environ.get("QCRBOX_REGISTRY_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_REGISTRY_PORT", 11000))
    url = f"http://{host}:{port}"
    return url
