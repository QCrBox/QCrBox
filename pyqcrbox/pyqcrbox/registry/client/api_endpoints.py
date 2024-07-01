from litestar import Litestar, MediaType, get
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogPlugin

__all__ = ["create_client_asgi_server"]


@get(path="/healthcheck", media_type=MediaType.TEXT, exclude_from_logs=True)
async def health_check() -> str:
    return "healthy"


logging_middleware_config = LoggingMiddlewareConfig(exclude_opt_key="exclude_from_logs")


def create_client_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[health_check],
        lifespan=[custom_lifespan],
        plugins=[StructlogPlugin()],
        middleware=[logging_middleware_config.middleware],
        openapi_config=None,
    )
    return app
