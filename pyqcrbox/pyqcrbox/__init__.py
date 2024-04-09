# SPDX-License-Identifier: MPL-2.0

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pyqcrbox")
except PackageNotFoundError:
    raise RuntimeError("The 'pyqcrbox' package is not correctly installed. Please install it with pip.")

# Import logging module here to ensure the loggers
# are set up correctly before any commands are run.
from . import logging
from .settings import settings
