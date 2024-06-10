import sqlalchemy
from litestar import Litestar, MediaType, Response, get, post
from litestar.openapi import OpenAPIConfig

__all__ = ["create_server_asgi_server"]

from sqlmodel import select

from pyqcrbox import logger, settings, sql_models


@get("/", media_type=MediaType.TEXT, include_in_schema=False)
async def hello() -> str:
    return "Hello from QCrBox!"


@get(path="/healthcheck", media_type=MediaType.TEXT)
async def health_check() -> str:
    return "healthy"


# @get(path="/applications", media_type=MediaType.JSON, return_dto=sql_models.ApplicationReadDTO)
@get(path="/applications", media_type=MediaType.JSON)
async def retrieve_applications() -> list[sql_models.ApplicationSpecWithCommands]:
    model_cls = sql_models.ApplicationSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        applications = session.scalars(select(model_cls)).all()
        applications = [app.to_read_model() for app in applications]
        return applications


@get(path="/commands", media_type=MediaType.JSON)
async def retrieve_commands() -> list[sql_models.CommandSpecWithParameters]:
    model_cls = sql_models.CommandSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        commands = session.scalars(select(model_cls)).all()
        commands = [cmd.to_read_model() for cmd in commands]
        return commands


@post(path="/invoke_command", media_type=MediaType.JSON)
async def invoke_command(data: sql_models.CommandInvocationCreate) -> dict:
    logger.info(f"[DDD] Received {data=}")
    return data.model_dump()


@post(path="/invoke_command/{cmd_id:int}", media_type=MediaType.JSON)
async def invoke_command_by_id(cmd_id: int) -> dict | Response[str]:
    logger.info(f"[DDD] Invoking command with id {cmd_id}")
    with settings.db.get_session() as session:
        try:
            command = session.get_one(sql_models.CommandSpecDB, cmd_id)
            return command.model_dump()
        except sqlalchemy.orm.exc.NoResultFound:
            return Response(f"Command not found with id={cmd_id}", status_code=404)


def create_server_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[
            hello,
            health_check,
            retrieve_applications,
            retrieve_commands,
            invoke_command,
            invoke_command_by_id,
        ],
        debug=True,
        lifespan=[custom_lifespan],
        openapi_config=OpenAPIConfig(title="QCrBox Server API", version="0.1"),
    )
    return app
