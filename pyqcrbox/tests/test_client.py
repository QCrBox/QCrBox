import pytest

from pyqcrbox import msg_specs


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_client, rabbit_test_broker, using_mock_rabbitmq_broker):
    msg = {"action": "health_check", "payload": {}}
    expected_response = msg_specs.responses.health_check_healthy()
    if not using_mock_rabbitmq_broker:
        expected_response = expected_response.model_dump()

    private_routing_key = test_client.private_routing_key

    if using_mock_rabbitmq_broker:
        assert not test_client.handler_was_called(private_routing_key)

    response = await rabbit_test_broker.publish(msg, private_routing_key, rpc=True)

    if using_mock_rabbitmq_broker:
        test_client.get_mock_handler(private_routing_key).assert_called_once_with(msg)

    assert response == expected_response
