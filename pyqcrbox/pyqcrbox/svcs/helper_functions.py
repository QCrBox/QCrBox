import svcs

__all__ = ["QCRBOX_SVCS_REGISTRY"]

from faststream.nats import NatsBroker

QCRBOX_SVCS_REGISTRY = svcs.Registry()


async def get_nats_broker():
    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        nats_broker = await con.aget(NatsBroker)
        return nats_broker


async def get_nats_key_value(bucket: str):
    nats_broker = await get_nats_broker()
    return await nats_broker.key_value(bucket=bucket)
