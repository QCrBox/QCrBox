import sys
from pathlib import Path

import pytest
from faststream.rabbit import TestRabbitBroker

from pyqcrbox.registry.server import TestQCrBoxServer, create_rabbitmq_broker

#
# Insert the QCrBox repository root at the beginning of `sys.path`.
# This ensures that `import pyqcrbox` will always import the local
# version of `pyqcrbox` (even if it is already installed in the
# current virtual environment) and that the tests are run against
# this local version.
#
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sample_application_spec():
    return {
        "name": "Olex2",
        "slug": "olex2",
        "version": "x.y.z",
    }


@pytest.fixture
async def create_qcrbox_test_server():
    broker = create_rabbitmq_broker()
    async with TestRabbitBroker(broker, with_real=False):
        # Note: we need to define this helper function *inside* the `async with` block
        #       that patches the broker
        def _create_qcrbox_test_server():
            test_server = TestQCrBoxServer(broker=broker)
            return test_server

        yield _create_qcrbox_test_server
