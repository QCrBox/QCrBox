# SPDX-License-Identifier: MPL-2.0
import logging
import sys
from pathlib import Path
from typing import assert_never

import structlog
from faststream import context

from pyqcrbox.settings import StructlogRendererEnum, get_log_level_as_int, settings

# ------------------------------------------------------------------------------
# This sets up the basic logging level so only QCrBox should appear as JSON
# ------------------------------------------------------------------------------

logging.basicConfig(
    format="(name)s | %(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# ------------------------------------------------------------------------------
# This sets up the structlog logger, which is used by QCrBox to output
# structured log messages
# ------------------------------------------------------------------------------


def get_log_level(level):
    if isinstance(level, str):
        level_as_int = get_log_level_as_int(level)
    elif isinstance(level, int):
        level_as_int = level
    else:
        raise TypeError(
            f"Argument 'level' must be a string or integer representing a valid logging level, got: {level!r}"
        )

    return level_as_int


def set_log_level(level):
    level_as_int = get_log_level(level)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level_as_int))


def merge_faststream_contextvars(
    _: structlog.types.WrappedLogger,
    __: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict["extra"] = event_dict.get(
        "extra",
        context.get_local("log_context") or {},
    )
    return event_dict


shared_processors = [
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.add_log_level,
    merge_faststream_contextvars,
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
]

match settings.logging.renderer:
    case StructlogRendererEnum.CONSOLE:
        # E.g. terminal session
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]
    case StructlogRendererEnum.JSON:
        # E.g. docker container session
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    case _:
        processors = []
        assert_never(settings.logging.renderer)


log_file = Path("qcrbox_app").with_suffix(".log")
structlog.configure(
    processors=processors,
    logger_factory=structlog.WriteLoggerFactory(file=log_file.open("wt")),
    wrapper_class=structlog.make_filtering_bound_logger(get_log_level(settings.logging.log_level_as_int)),
    cache_logger_on_first_use=False,
)
logger = structlog.get_logger()
