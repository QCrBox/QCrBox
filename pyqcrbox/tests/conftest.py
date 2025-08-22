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