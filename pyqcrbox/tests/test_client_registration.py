import logging

import pytest
from anyio import create_task_group
from faststream.rabbit import RabbitBroker, TestRabbitBroker

from pyqcrbox import msg_specs, sql_models
from pyqcrbox.registry import create_client_faststream_app, create_server_faststream_app


@pytest.fixture
def sample_application_cfg():
    return sql_models.ApplicationCreate(
        name="Olex2",
        slug="olex2_linux",
        version="x.y.z",
        description=None,
        url="https://www.olexsys.org/olex2/",
        email="helpdesk@olexsys.org",
        commands=[
            sql_models.CommandCreate(
                name="refine_iam",
                implemented_as=sql_models.command.ImplementedAs("CLI"),
                parameters=[
                    sql_models.ParameterCreate(name="cif_file", type="str"),
                    sql_models.ParameterCreate(name="ls_cycles", type="int", required=False, default_value=5),
                    sql_models.ParameterCreate(name="weight_cycles", type="int", required=False, default_value=5),
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_client_registration_during_startup(sample_application_cfg):
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
