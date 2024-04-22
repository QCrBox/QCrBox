from litestar import Litestar, MediaType, get
from litestar.openapi import OpenAPIConfig

__all__ = ["create_asgi_server"]


@get("/", media_type=MediaType.TEXT, include_in_schema=False)
async def hello() -> str:
    return "Hello from QCrBox!"


@get(path="/health-check", media_type=MediaType.TEXT)
async def health_check() -> str:
    return "healthy"


def create_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[hello, health_check],
        lifespan=[custom_lifespan],
        openapi_config=OpenAPIConfig(title="QCrBox Server API", version="0.0.1"),
    )
    return app
