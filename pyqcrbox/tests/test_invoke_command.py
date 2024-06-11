import pytest

from pyqcrbox import db_helpers, msg_specs, settings, sql_models
from pyqcrbox.msg_specs import ResponseStatusEnum


@pytest.mark.anyio
async def test_invoke_command(
    rabbit_test_broker,
    test_server,
    test_client,
    server_public_queue_name,
    using_mock_rabbitmq_broker,
):
    routing_key_qcrbox_registry = settings.rabbitmq.routing_key_qcrbox_registry
    application_routing_key = "qcrbox_rk_dummy_application_x.y.z"

    cmd_name = "greet_and_sleep"
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
    response = await rabbit_test_broker.publish(
        msg_invoke_cmd, routing_key_qcrbox_registry, rpc=True, raise_timeout=True
    )

    assert response["status"] == ResponseStatusEnum.OK
    correlation_id = response["payload"]["correlation_id"]

    # Check that the QCrBox server received the 'invoke_command' message
    if using_mock_rabbitmq_broker:
        test_server.get_mock_handler(server_public_queue_name).assert_any_call(msg_invoke_cmd)

        # Check that the server sends a command invocation request and this is picked up by the client
        expected_msg_command_invocation_request = msg_specs.CommandInvocationRequest(
            action="command_invocation_request",
            payload=msg_specs.PayloadForCommandInvocationRequest(
                application_slug="dummy_application",
                application_version="x.y.z",
                command_name=cmd_name,
                arguments={},
                correlation_id=correlation_id,
            ),
        ).model_dump()
        test_client.get_mock_handler(application_routing_key).assert_any_call(expected_msg_command_invocation_request)

        # Check that the client sends a reply to accept the command invocation request
        expected_msg_accept_command_invocation_request = msg_specs.ClientIndicatesAvailabilityToExecuteCommand(
            action="client_is_available_to_execute_command",
            payload=msg_specs.PayloadForClientIsAvailableToExecuteCommand(
                cmd_invocation_payload=msg_invoke_cmd["payload"],
                private_routing_key=test_client.private_routing_key,
            ),
        ).model_dump()
        test_server.get_mock_handler(routing_key_qcrbox_registry).assert_any_call(
            expected_msg_accept_command_invocation_request
        )

        # Check that the server sends the 'execute_command' message to the client
        expected_msg_execute_command = msg_specs.ExecuteCommand(
            action="execute_command",
            payload=msg_specs.PayloadForExecuteCommand(
                private_routing_key=test_client.private_routing_key,
                **expected_msg_command_invocation_request["payload"],
            ),
        ).model_dump()
        test_client.get_mock_handler(test_client.private_routing_key).assert_any_call(expected_msg_execute_command)
