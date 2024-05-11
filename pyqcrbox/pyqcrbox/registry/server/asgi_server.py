from litestar import Litestar, MediaType, get
from litestar.openapi import OpenAPIConfig

__all__ = ["create_server_asgi_server"]

from sqlmodel import select

from pyqcrbox import settings, sql_models


@get("/", media_type=MediaType.TEXT, include_in_schema=False)
async def hello() -> str:
    return "Hello from QCrBox!"


@get(path="/health-check", media_type=MediaType.TEXT)
async def health_check() -> str:
    return "healthy"


@get(path="/applications", media_type=MediaType.JSON, return_dto=sql_models.ApplicationReadDTO)
async def retrieve_applications() -> list[sql_models.ApplicationSpecDB]:
    model_cls = sql_models.ApplicationSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        applications = session.scalars(select(model_cls)).all()
        return applications


@get(path="/commands", media_type=MediaType.JSON)
async def retrieve_commands() -> list[sql_models.CommandSpecDB]:
    model_cls = sql_models.CommandSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        commands = session.scalars(select(model_cls)).all()
        return commands


def create_server_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[hello, health_check, retrieve_applications, retrieve_commands],
        lifespan=[custom_lifespan],
        openapi_config=OpenAPIConfig(title="QCrBox Server API", version="0.0.1"),
    )
    return app
