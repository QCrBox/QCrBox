import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

import pytest
from faststream.rabbit import RabbitBroker, TestRabbitBroker

sys._qcrbox_running_inside_tests = True  # noqa

from pyqcrbox import logger, sql_models
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

CURRENT_DIRECTORY = Path(__file__).parent


def _convert_str_to_bool(value):
    if not isinstance(value, str):
        raise TypeError(f"Value must be a string, got: {value} ({type(value)})")
    else:
        match value.lower():
            case "true":
                return True
            case "false":
                return False
            case _:
                raise ValueError(f"Value must be 'true' or 'false', got: {value!r}")


def pytest_addoption(parser):
    parser.addoption(
        "--with-real-rabbitmq",
        action="store",
        type=_convert_str_to_bool,
        help="run tests using the real RabbitMQ broker",
    )


if settings.testing.use_in_memory_db:
    logger.debug("Tests will use in-memory SQLite databases.")
else:
    logger.debug("Tests will use on-disk SQLite database in temporary directories.")

    @pytest.fixture(autouse=True)
    def set_sqlite_test_db_path(tmp_path):
        test_db_path = tmp_path / "test_db.sqlite"
        logger.warning(
            "Explicitly assigning a database url to `settings.db.url` will likely break if "
            "tests are executed in parallel. We should use dependency injection instead."
        )
        logger.debug(f"Test db path: {test_db_path}")
        settings.db.url = f"sqlite:///{test_db_path}"
        return test_db_path


def pytest_collection_modifyitems(config, items):
    match config.getoption("--with-real-rabbitmq"):
        case True:
            settings.testing.use_real_rabbitmq_broker = True
        case False:
            settings.testing.use_real_rabbitmq_broker = False
        case None:
            pass

    logger.debug(f"Tests are being run with real RabbitMQ broker: {settings.testing.use_real_rabbitmq_broker}")

    mark_skip_with_real_rabbitmq = pytest.mark.skipif(
        settings.testing.use_real_rabbitmq_broker,
        reason="Test requires mock RabbitMQ broker but running with real broker",
    )
    mark_xfail_with_real_rabbitmq = pytest.mark.xfail(
        reason="This test is not currently working with a real RabbitMQ broker",
    )

    for item in items:
        if item.get_closest_marker("requires_mock_rabbitmq_broker") is not None:
            item.add_marker(mark_skip_with_real_rabbitmq)
        if (
            item.get_closest_marker("xfail_with_real_rabbitmq_broker") is not None
            and settings.testing.use_real_rabbitmq_broker
        ):
            item.add_marker(mark_xfail_with_real_rabbitmq)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def using_mock_rabbitmq_broker():
    return not settings.testing.use_real_rabbitmq_broker


@pytest.fixture
def sample_application_spec():
    spec_yaml_file = CURRENT_DIRECTORY.joinpath("sample_application_spec.yaml")
    return sql_models.ApplicationSpecCreate.from_yaml_file(spec_yaml_file)


@pytest.fixture
async def rabbit_test_broker():
    broker = RabbitBroker(settings.rabbitmq.url)
    async with TestRabbitBroker(broker, with_real=settings.testing.use_real_rabbitmq_broker):
        yield broker


@pytest.fixture
def create_qcrbox_test_server(rabbit_test_broker) -> Callable[[], TestQCrBoxServer]:
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
        private_routing_key: str = "qcrbox_rk_test_client_xyz",
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


@pytest.fixture(scope="session")
def server_public_queue_name():
    return settings.rabbitmq.routing_key_qcrbox_registry
