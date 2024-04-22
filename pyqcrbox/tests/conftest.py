import sys
from pathlib import Path

import pytest
from faststream.rabbit import TestRabbitBroker

from pyqcrbox.registry.client import TestQCrBoxClient, set_up_client_rabbitmq_broker
from pyqcrbox.registry.server import TestQCrBoxServer, create_server_rabbitmq_broker

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
    broker = create_server_rabbitmq_broker()
    async with TestRabbitBroker(broker, with_real=False):
        # Note: we need to define this helper function *inside* the `async with` block
        #       that patches the broker
        def _create_qcrbox_test_server():
            test_server = TestQCrBoxServer(broker=broker)
            return test_server

        yield _create_qcrbox_test_server


@pytest.fixture
async def create_qcrbox_test_client():
    private_routing_key = "rk_qcrbox_test_private_routing_key"
    test_client = TestQCrBoxClient()
    set_up_client_rabbitmq_broker(test_client.broker, private_routing_key=private_routing_key)
    async with TestRabbitBroker(test_client.broker, with_real=False):
        # Note: we need to define this helper function *inside* the `async with` block
        #       that patches the broker
        def _create_qcrbox_test_client():
            return test_client

        yield _create_qcrbox_test_client


@pytest.fixture
def test_server(create_qcrbox_test_server):
    return create_qcrbox_test_server()


@pytest.fixture
def test_client(create_qcrbox_test_client):
    return create_qcrbox_test_client()
