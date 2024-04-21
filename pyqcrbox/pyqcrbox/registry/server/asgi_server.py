from litestar import Litestar, MediaType, get

__all__ = ["create_asgi_server"]


@get("/", media_type=MediaType.TEXT)
async def hello() -> str:
    return "Hello from QCrBox!"


@get(path="/health-check", media_type=MediaType.TEXT)
async def health_check() -> str:
    return "healthy"


def create_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar([hello, health_check], lifespan=[custom_lifespan])
    return app
