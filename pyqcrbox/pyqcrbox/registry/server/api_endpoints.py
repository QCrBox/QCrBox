import asyncio

import sqlalchemy
import svcs
from faststream.rabbit import RabbitBroker
from litestar import Litestar, MediaType, Response, get, post
from litestar.exceptions import HTTPException
from litestar.openapi import OpenAPIConfig

__all__ = ["create_server_asgi_server"]

from sqlmodel import select

from pyqcrbox import QCRBOX_SVCS_REGISTRY, logger, msg_specs, settings, sql_models


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


async def _invoke_command_impl(cmd: sql_models.CommandInvocationCreate, broker: RabbitBroker):
    msg = msg_specs.InvokeCommand(payload=cmd)

    try:
        # send command invocation request to any available clients
        await broker.publish(
            msg,
            settings.rabbitmq.routing_key_qcrbox_registry,
            rpc=False,
            # raise_timeout=True,
            # rpc_timeout=settings.rabbitmq.rpc_timeout,
        )
    except (TimeoutError, asyncio.exceptions.CancelledError) as exc:
        # raise TimeoutError(f"{exc}")
        raise HTTPException(f"{exc}")


@post(path="/commands/invoke", media_type=MediaType.JSON)
async def commands_invoke(data: sql_models.CommandInvocationCreate) -> dict:
    logger.info(f"[DDD] Received {data=}")

    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        broker = await con.aget(RabbitBroker)

    await _invoke_command_impl(data, broker)

    return dict(
        msg="Accepted command invocation request",
        status="ok",
        payload={
            "correlation_id": data.correlation_id,
        },
    )


@get(path="/calculations/{calculation_id:int}", media_type=MediaType.JSON)
async def get_calculation_info(calculation_id: int) -> dict | Response[dict]:
    with settings.db.get_session() as session:
        try:
            calc = session.get_one(sql_models.CalculationDB, calculation_id)
            response_data = {
                "id": calc.id,
                "status": calc.status,
            }
            return response_data
        except sqlalchemy.orm.exc.NoResultFound:
            return Response({"msg": f"No calculation exists with id={calculation_id}"}, status_code=404)


def create_server_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[
            hello,
            health_check,
            retrieve_applications,
            retrieve_commands,
            commands_invoke,
            get_calculation_info,
        ],
        debug=True,
        lifespan=[custom_lifespan],
        openapi_config=OpenAPIConfig(title="QCrBox Server API", version="0.1"),
    )
    return app
