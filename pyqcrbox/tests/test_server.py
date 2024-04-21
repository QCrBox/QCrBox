import pytest


@pytest.mark.anyio
async def test_ping_server(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()
    msg = {"action": "ping", "payload": {}}

    assert not test_server.get_mock_handler("qcrbox-registry").called

    async with test_server.run():
        await test_server.publish("qcrbox-registry", msg)

    test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(msg)
