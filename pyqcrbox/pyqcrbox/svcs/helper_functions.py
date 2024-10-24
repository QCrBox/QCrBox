import svcs

__all__ = ["QCRBOX_SVCS_REGISTRY", "get_nats_broker", "get_nats_key_value"]

from faststream.nats import NatsBroker

from pyqcrbox.settings import settings

QCRBOX_SVCS_REGISTRY = svcs.Registry()


def _create_nats_broker_instance():
    """
    Convenience function to create a NatsBroker instance with the correct settings.
    """
    return NatsBroker(settings.nats.url, graceful_timeout=10, max_reconnect_attempts=1)


async def get_nats_broker(connect=False):
    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        try:
            nats_broker = await con.aget(NatsBroker)
        except svcs.exceptions.ServiceNotFoundError:
            nats_broker = _create_nats_broker_instance()

        if connect:
            await nats_broker.connect()

        return nats_broker


async def get_nats_key_value(bucket: str):
    nats_broker = await get_nats_broker()
    return await nats_broker.key_value(bucket=bucket)
