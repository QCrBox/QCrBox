import pytest
from aioresult import ResultCapture
from anyio import create_task_group
from httpx import AsyncClient


@pytest.mark.anyio
async def test_ping_server_via_rabbitmq(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()
    msg = {"action": "ping", "payload": {}}

    assert not test_server.get_mock_handler("qcrbox-registry").called

    async with test_server.run():
        await test_server.publish("qcrbox-registry", msg)

    test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(msg)


@pytest.mark.anyio
async def test_ping_server_via_web_api(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()

    async with test_server.run():
        async with AsyncClient() as ac, create_task_group() as tg:
            res = ResultCapture.start_soon(tg, ac.get, "http://127.0.0.1:8000/")

        response = res.result()
        assert response.status_code == 200
        breakpoint()
        assert response.json() == {"msg": "Hello from QCrBox!"}
