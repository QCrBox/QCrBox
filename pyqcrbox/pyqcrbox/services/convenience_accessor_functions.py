import svcs
from faststream.nats import NatsBroker

from pyqcrbox.data_management import DataFileManager
from pyqcrbox.services.services_registry import QCRBOX_GLOBAL_SERVICES_REGISTRY


async def get_data_file_manager() -> DataFileManager:
    with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as con:
        return await con.aget(DataFileManager)


async def get_nats_broker(connect=False) -> NatsBroker:
    with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as con:
        broker = await con.aget(NatsBroker)
        if connect:
            await broker.connect()
        return broker


async def get_nats_key_value(bucket: str):
    nats_broker = await get_nats_broker()
    return await nats_broker.key_value(bucket=bucket)
