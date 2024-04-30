import pytest
from litestar.status_codes import HTTP_200_OK

from pyqcrbox import db_helpers, msg_specs, sql_models


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_server, rabbit_test_broker, server_public_queue_name):
    msg = {"action": "health_check", "payload": {}}
    assert not test_server.get_mock_handler(server_public_queue_name).called

    response = await rabbit_test_broker.publish(msg, server_public_queue_name, rpc=True)

    test_server.get_mock_handler(server_public_queue_name).assert_called_once_with(msg)
    assert response.status == "success"
    assert response.msg == "healthy"
    assert response.payload.dict() == {"health_status": "healthy"}


@pytest.mark.anyio
async def test_hello(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello from QCrBox!"


@pytest.mark.anyio
async def test_health_check_via_web_api(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


@pytest.mark.anyio
async def test_register_application(test_server, rabbit_test_broker, server_public_queue_name, sample_application_spec):
    msg = msg_specs.RegisterApplication(
        action="register_application",
        payload=msg_specs.PayloadForRegisterApplication(
            application_spec=sample_application_spec,
            private_routing_key="qcrbox_rk_private",
        ),
    )

    # Ensure we're starting with an empty database
    assert db_helpers.table_is_empty(sql_models.ApplicationSpecDB)

    # Send registration message to the server
    response = await rabbit_test_broker.publish(msg, server_public_queue_name, rpc=True)

    # Check that we received a successful response
    assert response.status == "success"
    # assert response.payload.application_id == 1

    # Check that the application spec was saved to the database
    result = db_helpers.get_one(
        sql_models.ApplicationSpecDB,
        slug=sample_application_spec.slug,
        version=sample_application_spec.version,
    )
    assert result.name == sample_application_spec.name
    assert result.slug == sample_application_spec.slug
    assert result.version == sample_application_spec.version
