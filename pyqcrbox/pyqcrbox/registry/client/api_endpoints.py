from litestar import Litestar, MediaType, get

from pyqcrbox.registry.shared import structlog_plugin

__all__ = ["create_client_asgi_server"]


@get(path="/healthz", media_type=MediaType.JSON, skip_logging=True)
async def health_check() -> dict:
    return {"status": "ok"}


def create_client_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[health_check],
        lifespan=[custom_lifespan],
        plugins=[structlog_plugin],
        openapi_config=None,
    )
    return app
