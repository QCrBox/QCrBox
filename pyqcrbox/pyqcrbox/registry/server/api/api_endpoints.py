from typing import Any

from litestar import MediaType, Router, get

__all__ = ["api_router"]


@get("/", media_type=MediaType.JSON, include_in_schema=False)
async def api_root_handler() -> dict[str, Any]:
    return {"message": "Hello world!"}


@get(path="/healthz", media_type=MediaType.JSON, skip_logging=False)
async def health_check() -> dict:
    return {"status": "ok"}


api_router = Router(
    path="/api",
    route_handlers=[api_root_handler, health_check],
)
