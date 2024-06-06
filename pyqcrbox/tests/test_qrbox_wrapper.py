import pytest


@pytest.mark.anyio
async def test_qcrbox_wrapper_1(test_server):
    async with test_server.qcrbox_web_client() as web_client:
        _ = web_client
