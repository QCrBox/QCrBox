import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import svcs
from faststream.nats import NatsBroker

from pyqcrbox.data_management import DataManager
from pyqcrbox.services import QCRBOX_GLOBAL_SERVICES_REGISTRY

sys._qcrbox_running_inside_tests = True


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def sample_data_dir() -> Path:
    return Path(__file__).parent.joinpath("sample_data")


@pytest.fixture(scope="session")
def sample_cif_file(sample_data_dir: Path) -> Path:
    return sample_data_dir.joinpath("periodic_table.cif")

@pytest.fixture(scope="session")
def sample_json_file(sample_data_dir: Path) -> Path:
    return sample_data_dir.joinpath("periodic_table.json")


@pytest.fixture
def clean_registry_db(tmp_path):
    """Provide an empty, file-backed registry database.

    A file-backed database (rather than the default in-memory one) is needed
    because the in-memory SQLite database is per-connection/per-thread, while
    e.g. Litestar's TestClient executes handlers in a separate thread.
    """
    from pyqcrbox.settings import settings

    original_url = settings.db.url
    settings.db.url = f"sqlite:///{tmp_path / 'test_registry_db.sqlite'}"
    try:
        settings.db.create_db_and_tables()
        yield
    finally:
        settings.db.url = original_url


@pytest.fixture(scope="session")
async def nats_broker() -> AsyncGenerator[NatsBroker, None]:
    async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
        broker = await container.aget(NatsBroker)
        await broker.connect()
        yield broker


@pytest.fixture(scope="session")
async def data_manager() -> AsyncGenerator[DataManager, None]:

    async with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as container:
        manager = await container.aget(DataManager)
        yield manager