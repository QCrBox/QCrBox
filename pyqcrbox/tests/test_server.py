import pytest
from litestar.status_codes import HTTP_200_OK


@pytest.mark.anyio
async def test_health_check_via_rabbitmq(test_server, rabbit_test_broker):
    msg = {"action": "health_check", "payload": {}}
    assert not test_server.get_mock_handler("qcrbox-registry").called

    response = await rabbit_test_broker.publish(msg, "qcrbox-registry", rpc=True)

    test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(msg)
    assert response.status == "success"
    assert response.msg == "healthy"
    assert response.payload.dict() == {"health_status": "healthy"}


@pytest.mark.anyio
async def test_hello(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello from QCrBox!"


@pytest.mark.anyio
async def test_health_check_via_web_api(test_server):
    async with test_server.web_client() as web_client:
        response = await web_client.get("/health-check")
        assert response.status_code == HTTP_200_OK
        assert response.text == "healthy"
