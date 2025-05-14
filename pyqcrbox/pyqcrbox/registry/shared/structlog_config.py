import structlog
from litestar.logging import StructLoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

from pyqcrbox import settings
from pyqcrbox.logging import get_log_level, processors

structlog_plugin = StructlogPlugin(
    config=StructlogConfig(
        structlog_logging_config=StructLoggingConfig(
            processors=processors,
            logger_factory=structlog.PrintLoggerFactory(),
            # logger_factory=structlog.WriteLoggerFactory(Path("app").with_suffix(".log").open("a")),
            wrapper_class=structlog.make_filtering_bound_logger(get_log_level(settings.logging.log_level_as_int)),
            cache_logger_on_first_use=False,
        ),
        middleware_logging_config=LoggingMiddlewareConfig(
            exclude_opt_key="skip_logging",
            request_log_fields=["method", "path", "path_params", "query"],
            response_log_fields=["status_code", "body"],
        ),
    )
)
