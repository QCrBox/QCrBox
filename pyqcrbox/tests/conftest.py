import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from faststream.rabbit import TestRabbitBroker

from pyqcrbox.registry.client import TestQCrBoxClient, set_up_client_rabbitmq_broker
from pyqcrbox.registry.server import TestQCrBoxServer, set_up_server_rabbitmq_broker

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
def create_qcrbox_test_server():
    @asynccontextmanager
    async def _create_qcrbox_test_server():
        test_server = TestQCrBoxServer()
        set_up_server_rabbitmq_broker(test_server.broker)
        async with TestRabbitBroker(test_server.broker, with_real=False):
            yield test_server

    return _create_qcrbox_test_server


@pytest.fixture
def create_qcrbox_test_client():
    @asynccontextmanager
    async def _create_qcrbox_test_client(private_routing_key: str = "rk_qcrbox_test_private_routing_key"):
        test_client = TestQCrBoxClient()
        set_up_client_rabbitmq_broker(test_client.broker, private_routing_key=private_routing_key)
        async with TestRabbitBroker(test_client.broker, with_real=False):
            yield test_client

    return _create_qcrbox_test_client


@pytest.fixture
async def test_server(create_qcrbox_test_server):
    async with create_qcrbox_test_server() as test_server:
        yield test_server


@pytest.fixture
async def test_client(create_qcrbox_test_client):
    async with create_qcrbox_test_client() as test_client:
        yield test_client
