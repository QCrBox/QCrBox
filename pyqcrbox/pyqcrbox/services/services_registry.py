import svcs
from faststream.nats import NatsBroker

from pyqcrbox import settings
from pyqcrbox.data_management import DataFileManager, DummyDataFileManager


class DevelopmentServicesRegistry(svcs.Registry):
    def __init__(self):
        super().__init__()

        # self.register_value(DataFileManager, DataFileManager())
        self.register_value(DataFileManager, DummyDataFileManager())
        self.register_factory(NatsBroker, self.create_nats_broker)

    def create_nats_broker(self):
        return NatsBroker(settings.nats.url, graceful_timeout=10, max_reconnect_attempts=1)


def get_qcrbox_services_registry():
    # For now, we're just using the development registry. In the future,
    # we may want to use different registries for different environments
    # (e.g., development, testing, production).
    return DevelopmentServicesRegistry()


QCRBOX_GLOBAL_SERVICES_REGISTRY = get_qcrbox_services_registry()
