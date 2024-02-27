import logging

import pytest
from anyio import create_task_group
from faststream.rabbit import RabbitBroker, TestRabbitBroker

from pyqcrbox.registry import create_client_faststream_app, create_server_faststream_app


@pytest.fixture
def sample_application_cfg():
    return {
        "name": "Olex2",
        "slug": "olex2-linux",
        "version": "x.y.z",
        "description": None,
        "url": "https://www.olexsys.org/olex2/",
        "email": "helpdesk@olexsys.org",
    }


@pytest.mark.asyncio
async def test_server_and_client_v2(sample_application_cfg):
    private_queue_name = "qcrbox_rk_test_client_xyz"
    expected_registration_message = {
        "action": "register_application",
        "payload": {
            "application_config": sample_application_cfg,
            "routing_key__registry_to_application": private_queue_name,
        },
    }

    broker = RabbitBroker(graceful_timeout=10)
    async with TestRabbitBroker(broker, with_real=False):
        server_app = create_server_faststream_app(broker, log_level=logging.DEBUG)
        client_app = create_client_faststream_app(
            broker,
            private_queue_name=private_queue_name,
            application_spec=sample_application_cfg,
            log_level=logging.DEBUG,
        )

        async with create_task_group() as tg:
            server_max_messages = 1
            client_max_messages = 0
            tg.start_soon(server_app.run, server_max_messages)
            tg.start_soon(client_app.run, client_max_messages)

        server_app.on_qcrbox_registry.mock.assert_called_once_with(expected_registration_message)
