import pytest

from pyqcrbox.services import get_nats_broker


@pytest.mark.anyio
async def test_connection_to_nats_server():
    broker = await get_nats_broker()
    assert "nats://127.0.0.1:4222/" in broker.url
    assert broker._NatsBroker__is_connected is True
