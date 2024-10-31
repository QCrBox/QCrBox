from litestar.logging import StructLoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

structlog_plugin = StructlogPlugin(
    config=StructlogConfig(
        structlog_logging_config=StructLoggingConfig(),
        middleware_logging_config=LoggingMiddlewareConfig(
            exclude_opt_key="skip_logging",
            # request_log_fields=["method", "path", "path_params", "query"],
            # response_log_fields=["status_code"],
        ),
    )
)
