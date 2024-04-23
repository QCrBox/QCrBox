import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pyqcrbox import logger


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_server):
    msg = {"action": "health_check", "payload": {}}
    assert not test_server.get_mock_handler("qcrbox-registry").called

    async with test_server.run():
        await test_server.publish("qcrbox-registry", msg)

    test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(msg)
    logger.warning("TODO: verify the server response")


@pytest.mark.anyio
async def test_hello(test_server):
    async with test_server.run():
        async with AsyncTestClient(app=test_server.asgi_server) as web_client:
            response = await web_client.get("/")
            assert response.status_code == HTTP_200_OK
            assert response.text == "Hello from QCrBox!"


@pytest.mark.anyio
async def test_health_check_via_web_api(test_server):
    async with test_server.run():
        async with AsyncTestClient(app=test_server.asgi_server) as web_client:
            response = await web_client.get("/health-check")
            assert response.status_code == HTTP_200_OK
            assert response.text == "healthy"
