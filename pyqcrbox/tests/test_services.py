import pytest
from faststream.nats import NatsBroker

from pyqcrbox.data_management import DataManager


@pytest.mark.anyio
async def test_connection_to_nats_server(nats_broker: NatsBroker):
    assert "nats://127.0.0.1:4222/" in nats_broker.url
    assert nats_broker._NatsBroker__is_connected is True


@pytest.mark.anyio
async def test_connection_to_data_manager(data_manager: DataManager):
    assert "nats://127.0.0.1:4222/" in data_manager._nats_broker.url
    assert data_manager._nats_broker._NatsBroker__is_connected is True