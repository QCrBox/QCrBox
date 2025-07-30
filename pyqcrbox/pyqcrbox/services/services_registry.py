import svcs
from faststream.nats import NatsBroker

from pyqcrbox import settings
from pyqcrbox.data_management import DataFileManager, NatsDataFileManager
from pyqcrbox.logging import logger


def create_nats_broker():
    return NatsBroker(
        settings.nats.url,
        graceful_timeout=settings.nats.graceful_timeout,
        max_reconnect_attempts=settings.nats.max_reconnect_attempts,
        logger=logger,
    )

async def create_data_file_manager(container: svcs.Container):
    nats_broker = await container.aget(NatsBroker)
    return NatsDataFileManager(nats_broker)



QCRBOX_GLOBAL_SERVICES_REGISTRY = svcs.Registry()
QCRBOX_GLOBAL_SERVICES_REGISTRY.register_factory(NatsBroker, create_nats_broker)
QCRBOX_GLOBAL_SERVICES_REGISTRY.register_factory(DataFileManager, create_data_file_manager)
