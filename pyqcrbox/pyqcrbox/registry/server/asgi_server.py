from typing import Any

from litestar import Litestar, get

__all__ = ["create_asgi_server"]


@get("/")
async def hello() -> dict[str, Any]:
    return {"msg": "Hello from QCrBox!"}


def create_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar([hello], lifespan=[custom_lifespan])
    return app
