# SPDX-License-Identifier: MPL-2.0
from importlib.metadata import PackageNotFoundError, version

__all__ = ["logger", "settings"]

try:
    __version__ = version("pyqcrbox")
except PackageNotFoundError:
    raise RuntimeError("The 'pyqcrbox' package is not correctly installed. Please install it with pip.")


# Import logging module first to ensure the loggers
# are set up correctly before anything else is run.
from .logging import logger
from .settings import settings
