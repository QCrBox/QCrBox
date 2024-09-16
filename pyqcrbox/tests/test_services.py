import pytest

from pyqcrbox.services import get_nats_broker


@pytest.mark.anyio
async def test_get_nats_broker():
    broker = await get_nats_broker()
    kv = await broker.key_value("test")
    assert "nats://127.0.0.1:4222/" in broker.url
    assert broker._NatsBroker__is_connected is True
    #assert await kv.get("ping") == "pong"
