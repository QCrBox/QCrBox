import pytest
from anyio import create_task_group
from faststream.rabbit import RabbitBroker, TestRabbitBroker

from pyqcrbox import msg_specs
from pyqcrbox.registry import create_client_faststream_app, create_server_faststream_app


@pytest.mark.asyncio
async def test_client_registers_itself_with_server_during_startup(sample_application_cfg):
    private_queue_name = "qcrbox_rk_test_client_xyz"
    expected_registration_message = msg_specs.RegisterApplication(
        action="register_application",
        payload=msg_specs.RegisterApplication.Payload(
            application_config=sample_application_cfg,
            routing_key__registry_to_application=private_queue_name,
        ),
    ).dict()

    broker = RabbitBroker(graceful_timeout=10)
    async with TestRabbitBroker(broker, with_real=False):
        server_app = create_server_faststream_app(broker, log_level="DEBUG")
        client_app = create_client_faststream_app(
            broker,
            private_queue_name=private_queue_name,
            application_spec=sample_application_cfg,
            log_level="DEBUG",
        )

        async with create_task_group() as tg:
            server_max_messages = 1
            client_max_messages = 0
            tg.start_soon(server_app.run, server_max_messages)
            tg.start_soon(client_app.run, client_max_messages)

        server_app.on_qcrbox_registry.mock.assert_called_once_with(expected_registration_message)
        # TODO: verify that the client app receives a 'success' response.


@pytest.mark.asyncio
async def test_client_registration_succeeds_even_if_same_application_was_registered_before(sample_application_cfg):
    private_queue_name = "qcrbox_rk_test_client_xyz"
    expected_registration_message = msg_specs.RegisterApplication(
        action="register_application",
        payload=msg_specs.RegisterApplication.Payload(
            application_config=sample_application_cfg,
            routing_key__registry_to_application=private_queue_name,
        ),
    ).dict()

    broker = RabbitBroker(graceful_timeout=10)
    async with TestRabbitBroker(broker, with_real=False):
        server_app = create_server_faststream_app(broker, log_level="DEBUG")
        client_app_1 = create_client_faststream_app(
            broker, private_queue_name=private_queue_name, application_spec=sample_application_cfg, log_level="DEBUG"
        )
        client_app_2 = create_client_faststream_app(
            broker, private_queue_name=private_queue_name, application_spec=sample_application_cfg, log_level="DEBUG"
        )

        async with create_task_group() as tg:
            server_max_messages = 2
            client_1_max_messages = 0
            client_2_max_messages = 0
            tg.start_soon(server_app.run, server_max_messages)
            tg.start_soon(client_app_1.run, client_1_max_messages)
            tg.start_soon(client_app_2.run, client_2_max_messages)

        # TODO: it would be nice to use `assert_has_calls()` here (see [1]),
        #       but I ran into issues trying to get this to work so I'm using
        #       the slightly less exact comparison below for now.
        #          -- Max, 7th March 2024
        #
        #       [1] https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.assert_has_calls
        server_app.on_qcrbox_registry.mock.assert_called_with(expected_registration_message)
        assert server_app.on_qcrbox_registry.mock.call_count == 2

        # TODO: verify that the client apps receive a 'success' response.
