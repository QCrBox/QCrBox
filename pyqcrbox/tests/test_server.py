import pytest
from litestar.status_codes import HTTP_200_OK

from pyqcrbox import db_helpers, msg_specs, sql_models
from pyqcrbox.helpers import ensure_dict


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(
    test_server,
    rabbit_test_broker,
    server_public_queue_name,
    using_mock_rabbitmq_broker,
):
    msg = {"action": "health_check", "payload": {}}

    if using_mock_rabbitmq_broker:
        assert not test_server.get_mock_handler(server_public_queue_name).called

    response = await rabbit_test_broker.publish(msg, server_public_queue_name, rpc=True)

    if using_mock_rabbitmq_broker:
        response = ensure_dict(response)
        test_server.get_mock_handler(server_public_queue_name).assert_called_once_with(msg)

    assert response["status"] == "success"
    assert response["msg"] == "healthy"
    assert response["payload"] == {"health_status": "healthy"}


@pytest.mark.anyio
@pytest.mark.xfail_with_real_rabbitmq_broker
async def test_hello(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello from QCrBox!"


@pytest.mark.anyio
@pytest.mark.xfail_with_real_rabbitmq_broker
async def test_health_check_via_web_api(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"


@pytest.mark.anyio
async def test_register_application(
    test_server,
    rabbit_test_broker,
    server_public_queue_name,
    sample_application_spec,
    using_mock_rabbitmq_broker,
):
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
    if using_mock_rabbitmq_broker:
        response = ensure_dict(response)

    # Check that we received a successful response
    assert response["status"] == "success"
    # assert response.payload.application_id == 1

    # Check that the application spec was saved to the database
    app_db = db_helpers.get_one(
        sql_models.ApplicationSpecDB,
        slug=sample_application_spec.slug,
        version=sample_application_spec.version,
    )
    assert app_db.name == sample_application_spec.name
    assert app_db.slug == sample_application_spec.slug
    assert app_db.version == sample_application_spec.version

    command_spec = sample_application_spec.commands[0]
    cmd_db = db_helpers.get_one(
        sql_models.CommandSpecDB,
        name=command_spec.name,
    )
    assert cmd_db.name == command_spec.name
    assert cmd_db.implemented_as == command_spec.implemented_as


@pytest.mark.anyio
@pytest.mark.xfail_with_real_rabbitmq_broker
async def test_api_endpoint_applications(test_server, create_qcrbox_test_client, sample_application_spec):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/applications")
        assert response.status_code == HTTP_200_OK
        assert response.json() == []

        async with create_qcrbox_test_client() as test_client, test_client.run():
            response = await web_client.get("/applications")
            assert response.status_code == HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 1
            response_app = response_data[0]
            assert response_app["slug"] == "dummy_application"
            assert response_app["version"] == "x.y.z"


@pytest.mark.anyio
@pytest.mark.xfail_with_real_rabbitmq_broker
async def test_api_endpoint_commands(test_server, create_qcrbox_test_client, sample_application_spec):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/commands")
        assert response.status_code == HTTP_200_OK
        assert response.json() == []

        async with create_qcrbox_test_client() as test_client, test_client.run():
            response = await web_client.get("/commands")
            assert response.status_code == HTTP_200_OK
            response_data = response.json()
            assert len(response_data) == 1
            response_cmd = response_data[0]
            assert response_cmd["name"] == "greet_and_sleep"
            assert response_cmd["implemented_as"] == "python_callable"
