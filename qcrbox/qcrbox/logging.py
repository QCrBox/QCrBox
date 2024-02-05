# SPDX-License-Identifier: MPL-2.0

import sys

from loguru import logger


class Formatter:
    def __init__(self):
        self.fmt_default = "<green>{time:YYYY-mm-dd HH:MM:SS}</green> | {level: <8} | <level>{message}</level>\n"
        self.fmt_dry_run = "<magenta><bold>DRY-RUN</bold></magenta> | {level: <8} | <level>{message}</level>\n"
        # self.fmt_debug = (
        #     "<green>{time:YYYY-mm-dd HH:MM:SS}</green> | {process} | "
        #     "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"
        # )

    def format(self, record):
        is_dry_run = record.get("extra", {}).get("dry_run", False)
        if is_dry_run:
            return self.fmt_dry_run
        else:
            return self.fmt_default


formatter = Formatter()

logger.remove()
logger.add(sys.stderr, level="DEBUG", format=formatter.format)
