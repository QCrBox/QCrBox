import pytest

from pyqcrbox import logger


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_client):
    msg = {"action": "health_check", "payload": {}}

    private_routing_key = test_client.private_routing_key
    assert not test_client.handler_was_called(private_routing_key)

    await test_client.publish(private_routing_key, msg)

    test_client.get_mock_handler(private_routing_key).assert_called_once_with(msg)
    logger.warning("TODO: verify the client response")
