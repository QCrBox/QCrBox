import pytest

from pyqcrbox import logger


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_client):
    msg = {"action": "health_check", "payload": {}}

    assert not test_client.get_mock_handler("rk_qcrbox_test_private_routing_key").called

    await test_client.publish("rk_qcrbox_test_private_routing_key", msg)

    test_client.get_mock_handler("rk_qcrbox_test_private_routing_key").assert_called_once_with(msg)
    logger.warning("TODO: verify the client response")
