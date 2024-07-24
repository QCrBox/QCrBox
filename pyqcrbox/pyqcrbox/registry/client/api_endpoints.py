from litestar import Litestar, MediaType, get
from litestar.plugins.structlog import StructlogPlugin

__all__ = ["create_client_asgi_server"]


@get(path="/healthz", media_type=MediaType.JSON)
async def health_check() -> dict:
    return {"status": "ok"}


def create_client_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[health_check],
        lifespan=[custom_lifespan],
        plugins=[StructlogPlugin()],
        openapi_config=None,
    )
    return app
