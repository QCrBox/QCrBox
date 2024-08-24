# SPDX-License-Identifier: MPL-2.0
from typing import assert_never

import structlog
from faststream import context

from pyqcrbox.settings import StructlogRendererEnum, get_log_level_as_int, settings


def set_log_level(level):
    if isinstance(level, str):
        level_as_int = get_log_level_as_int(level)
    elif isinstance(level, int):
        level_as_int = level
    else:
        raise TypeError(
            f"Argument 'level' must be a string or integer representing a valid logging level, got: {level!r}"
        )

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(level_as_int))


def merge_faststream_contextvars(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    event_dict["extra"] = event_dict.get(
        "extra",
        context.get_local("log_context") or {},
    )
    return event_dict


shared_processors = [
    merge_faststream_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
]

match settings.logging.renderer:
    case StructlogRendererEnum.CONSOLE:
        # E.g. terminal session
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]
    case StructlogRendererEnum.JSON:
        print("[DDD] Case 2: Docker container session")
        # E.g. docker container session
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    case _:
        processors = []
        assert_never(settings.logging.renderer)


structlog.configure(
    processors=processors,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

# set_log_level(settings.logging.log_level_as_int)
#
logger = structlog.get_logger()
