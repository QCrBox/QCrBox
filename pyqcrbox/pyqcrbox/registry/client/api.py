from litestar import Litestar

__all__ = ["create_client_asgi_server"]


def create_client_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[],
        lifespan=[custom_lifespan],
        openapi_config=None,
    )
    return app
