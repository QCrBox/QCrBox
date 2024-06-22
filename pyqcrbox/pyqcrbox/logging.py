# SPDX-License-Identifier: MPL-2.0

from typing import assert_never

import structlog
from faststream import context

from pyqcrbox.settings import StructlogRendererEnum, settings


def merge_faststream_contextvars(
    logger: structlog.types.WrappedLogger,
    method_name: str,
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

logger = structlog.get_logger()
