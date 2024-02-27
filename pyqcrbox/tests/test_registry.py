import logging

import pytest
from anyio import create_task_group
from faststream.rabbit import RabbitBroker, TestRabbitBroker

from pyqcrbox.registry import create_client_faststream_app, create_server_faststream_app


@pytest.mark.asyncio
async def test_server_and_client_v2():
    broker = RabbitBroker(graceful_timeout=10)
    async with TestRabbitBroker(broker, with_real=False):
        client_app = create_client_faststream_app(broker, log_level=logging.DEBUG)
        server_app = create_server_faststream_app(broker, log_level=logging.DEBUG)

        async with create_task_group() as tg:
            server_max_messages = 1
            client_max_messages = 0
            tg.start_soon(server_app.run, server_max_messages)
            tg.start_soon(client_app.run, client_max_messages)
