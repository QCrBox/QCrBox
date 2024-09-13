import pytest

from pathlib import Path


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def sample_data_dir():
    return Path(__file__).parent.joinpath("sample_data")


@pytest.fixture(scope="session")
def sample_cif_file(sample_data_dir):
    return sample_data_dir.joinpath("periodic_table.cif")
