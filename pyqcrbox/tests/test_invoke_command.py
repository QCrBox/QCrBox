import pytest

from pyqcrbox import db_helpers, msg_specs, settings, sql_models


@pytest.mark.anyio
async def test_invoke_command(
    rabbit_test_broker,
    test_server,
    test_client,
    server_public_queue_name,
    # sample_application_spec,
):
    routing_key_qcrbox_registry = settings.rabbitmq.routing_key_qcrbox_registry
    # private_routing_key = "qcrbox_rk_test_client_xyz"
    application_routing_key = "qcrbox_rk_dummy_application_x.y.z"

    cmd_name = "say_hello"
    cmd_db = db_helpers.get_one_or_none(sql_models.CommandSpecDB, name=cmd_name)
    assert cmd_db is not None

    msg_invoke_cmd = msg_specs.InvokeCommand(
        action="invoke_command",
        payload=msg_specs.PayloadForInvokeCommand(
            application_slug="dummy_application",
            application_version="x.y.z",
            command_name=cmd_name,
            arguments={},
        ),
    ).model_dump()

    # Invoke the command by sending the 'invoke_command' message to the server's public RabbitMQ queue
    await rabbit_test_broker.publish(msg_invoke_cmd, routing_key_qcrbox_registry)
    # assert False, "TODO: implement the remainder of the test"

    # Check that the server received the 'invoke_command' message
    test_server.get_mock_handler(server_public_queue_name).assert_called_with(msg_invoke_cmd)

    # Check that the server sent a command invocation request which is picked up by the client
    expected_msg_command_invocation_request = msg_specs.CommandInvocationRequest(
        action="command_invocation_request",
        payload=msg_specs.PayloadForCommandInvocationRequest(
            application_slug="dummy_application",
            application_version="x.y.z",
            command_name=cmd_name,
            arguments={},
        ),
    )
    test_client.get_mock_handler(application_routing_key).assert_called_with(expected_msg_command_invocation_request)
