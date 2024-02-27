import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def insert_repo_root_into_sys_path():
    """
    Insert the QCrBox repository root at the beginning of `sys.path`.
    This ensures that `import pyqcrbox` will always import the local
    version of `pyqcrbox` (even if it is already installed in the
    current virtual environment) and that the tests are run against
    this local version.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
