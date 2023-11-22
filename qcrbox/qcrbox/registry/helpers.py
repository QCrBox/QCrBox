import asyncio
import os
from typing import Optional

from aiormq import AMQPConnectionError
from loguru import logger
from propan.fastapi import RabbitRouter
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type


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
    host = host or os.environ.get("QCRBOX_QCRBOX_REGISTRY_HOST", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_QCRBOX_REGISTRY_PORT", 11000))
    url = f"http://{host}:{port}"
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


def schedule_asyncio_task(coro, *, loop):
    """
    Execute a specific coroutine/task in a given event loop.
    Crucially, this does not depend on the event loop already running.

    If the event loop is currently running, this returns the scheduled task.
    In this case, the caller is responsible for ensuring that the task is done
    before depending on the result. The caller is also responsible for raising
    (or otherwise dealing with) any exceptions that the task produced.

    If the event loop is not currently running, the scheduled task is run until
    it is complete. In this case, None is returned.
    """
    # TODO: if the task raises an exception during execution, this is not immediately
    #       re-raised in case we're in an interactive environment such as a Jupyter
    #       notebook. We should wrap the coroutine in a little helper function which
    #       sends a signal once it is completed, and this signal should in turn be
    #       picked up by something that can check if the task completed successfully
    #       and/or re-raise any exceptions that occurred during execution. (Although
    #       I'm not entirely sure where this 'something' can live so that it can respond
    #       immediately...
    task = asyncio.ensure_future(coro, loop=loop)
    if loop.is_running():
        return task
    else:
        loop.run_until_complete(task)
        return None


class RabbitRouterWithConnectionRetries(RabbitRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broker.connect = wrap_with_retry(
            self.broker.connect,
            wait_interval=3,
            max_attempt_number=50,
        )
