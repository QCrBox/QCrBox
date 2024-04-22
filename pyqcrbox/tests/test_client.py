import pytest


# @pytest.mark.xfail(reason="Not checking for client response yet")
@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_client):
    msg = {"action": "health_check", "payload": {}}
    assert not test_client.get_mock_handler("rk_qcrbox_test_private_routing_key").called

    async with test_client.run():
        await test_client.publish("rk_qcrbox_test_private_routing_key", msg)

    test_client.get_mock_handler("rk_qcrbox_test_private_routing_key").assert_called_once_with(msg)
    # raise NotImplementedError("TODO: verify the client response")
