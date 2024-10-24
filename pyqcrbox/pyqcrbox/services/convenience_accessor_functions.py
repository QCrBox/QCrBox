import svcs
from faststream.nats import NatsBroker

from pyqcrbox.data_management import DataFileManager
from pyqcrbox.services.services_registry import QCRBOX_GLOBAL_SERVICES_REGISTRY


async def get_data_file_manager():
    with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as con:
        return await con.aget(DataFileManager)


async def get_nats_broker() -> NatsBroker:
    with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as con:
        broker = await con.aget(NatsBroker)
        await broker.connect()
        return broker
