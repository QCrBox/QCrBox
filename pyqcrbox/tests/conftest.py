import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from faststream.rabbit import RabbitBroker, TestRabbitBroker

from pyqcrbox import sql_models
from pyqcrbox.registry.client import TestQCrBoxClient
from pyqcrbox.registry.server import TestQCrBoxServer
from pyqcrbox.settings import settings

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
async def rabbit_test_broker():
    broker = RabbitBroker(settings.rabbitmq.url)
    async with TestRabbitBroker(broker, with_real=False):
        yield broker


@pytest.fixture
def create_qcrbox_test_server(rabbit_test_broker):
    @asynccontextmanager
    async def _create_qcrbox_test_server():
        test_server = TestQCrBoxServer(broker=rabbit_test_broker)
        yield test_server

    return _create_qcrbox_test_server


@pytest.fixture
def create_qcrbox_test_client(rabbit_test_broker, sample_application_spec):
    @asynccontextmanager
    async def _create_qcrbox_test_client(
        *,
        application_spec: sql_models.ApplicationSpecCreate = sample_application_spec,
        private_routing_key: str = "rk_qcrbox_test_private_routing_key",
    ):
        test_client = TestQCrBoxClient(
            broker=rabbit_test_broker,
            application_spec=application_spec,
            private_routing_key=private_routing_key,
        )
        yield test_client

    return _create_qcrbox_test_client


@pytest.fixture
async def test_server(create_qcrbox_test_server):
    async with create_qcrbox_test_server() as test_server, test_server.run(purge_existing_db_tables=False):
        yield test_server


@pytest.fixture
async def test_client(create_qcrbox_test_client):
    async with create_qcrbox_test_client() as test_client, test_client.run():
        yield test_client
