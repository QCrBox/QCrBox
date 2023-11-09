import os
from typing import Optional

from aiormq import AMQPConnectionError
from loguru import logger
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type


def get_rabbitmq_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    host = host or os.environ.get("QCRBOX_HOST_RABBITMQ", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_PORT_RABBITMQ", 5672))
    username = username or os.environ.get("QCRBOX_RABBITMQ_USERNAME", "guest")
    password = password or os.environ.get("QCRBOX_RABBITMQ_PASSWORD", "guest")
    url = f"amqp://{username}:{password}@{host}:{port}/"
    return url


def wrap_with_retry(orig_connect_func, *, wait_interval, max_attempt_number):
    @retry(
        reraise=True,
        wait=wait_fixed(wait_interval),
        stop=stop_after_attempt(max_attempt_number),
        retry=retry_if_exception_type(AMQPConnectionError),
    )
    async def connect_with_retries(*args, **kwargs):
        logger.debug("Attempting to establish connection to RabbitMQ.")
        await orig_connect_func(*args, **kwargs)

    return connect_with_retries
