from litestar import Litestar, MediaType, get

__all__ = ["create_client_asgi_server"]


@get(path="/health-check", media_type=MediaType.TEXT)
async def health_check() -> str:
    return "healthy"


def create_client_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[health_check],
        lifespan=[custom_lifespan],
        openapi_config=None,
    )
    return app
