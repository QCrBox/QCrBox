import sys
from pathlib import Path

import pytest
from loguru import logger

#
# Insert the QCrBox repository root at the beginning of `sys.path`.
# This ensures that `import pyqcrbox` will always import the local
# version of `pyqcrbox` (even if it is already installed in the
# current virtual environment) and that the tests are run against
# this local version.
#
sys.path.insert(0, str(Path(__file__).parent.parent))
from pyqcrbox import settings


@pytest.fixture(scope="function", autouse=True)
def adjust_settings_for_tests(request, tmp_path):
    """
    Modify the pyqcrbox settings so that they are more suitable for tests.

    This fixture is applied automatically when the tests are run but can be skipped
    for specific tests by using the decorator `@pytest.mark.no_adjust_settings`.
    """
    if "no_adjust_settings" in request.keywords:
        logger.debug(f"Skipping automatic adjustment of pyqcrbox settings for test: {request.node.name!r}")
        return
    settings.db.url = f"sqlite:///{tmp_path}/test_registry_db.sqlite"
