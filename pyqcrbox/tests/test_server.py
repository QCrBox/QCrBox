import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient


@pytest.mark.xfail(reason="Not checking for server response yet")
@pytest.mark.anyio
async def test_health_check_via_rabbitmq(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()
    msg = {"action": "health_check", "payload": {}}

    assert not test_server.get_mock_handler("qcrbox-registry").called

    async with test_server.run():
        await test_server.publish("qcrbox-registry", msg)

    test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(msg)
    raise NotImplementedError("TODO: verify the server response")


@pytest.mark.anyio
async def test_hello(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()

    async with test_server.run():
        async with AsyncTestClient(app=test_server.asgi_server) as web_client:
            response = await web_client.get("/")
            assert response.status_code == HTTP_200_OK
            assert response.text == "Hello from QCrBox!"


@pytest.mark.anyio
async def test_health_check_via_web_api(create_qcrbox_test_server):
    test_server = create_qcrbox_test_server()

    async with test_server.run():
        async with AsyncTestClient(app=test_server.asgi_server) as web_client:
            response = await web_client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"
        #
        # async with AsyncClient() as ac, create_task_group() as tg:
        #     res = ResultCapture.start_soon(tg, ac.get, "http://127.0.0.1:8000/")

        # response = res.result()
        # assert response.status_code == 200
        # breakpoint()
        # assert response.json() == {"msg": "Hello from QCrBox!"}
