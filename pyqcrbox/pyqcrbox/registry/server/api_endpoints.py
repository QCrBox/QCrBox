import json

import nats.js.errors
import sqlalchemy
import svcs
from faststream.nats import NatsBroker

# from faststream.rabbit import RabbitBroker
from litestar import Litestar, MediaType, Response, get, post
from litestar.openapi import OpenAPIConfig
from litestar.plugins.structlog import StructlogPlugin
from sqlalchemy.orm import joinedload

__all__ = ["create_server_asgi_server"]


from litestar.exceptions import ClientException
from sqlmodel import select

from pyqcrbox import QCRBOX_SVCS_REGISTRY, logger, msg_specs, settings, sql_models_NEW_v2
from pyqcrbox.svcs import get_nats_key_value


@get("/", media_type=MediaType.TEXT, include_in_schema=False)
async def hello() -> str:
    return "Hello from QCrBox!"


@get(path="/healthz", media_type=MediaType.JSON)
async def health_check() -> dict:
    return {"status": "ok"}


# @get(path="/applications", media_type=MediaType.JSON, return_dto=sql_models.ApplicationReadDTO)
@get(path="/applications", media_type=MediaType.JSON)
async def retrieve_applications() -> list[sql_models_NEW_v2.ApplicationSpecWithCommands]:
    model_cls = sql_models_NEW_v2.ApplicationSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        applications = session.scalars(select(model_cls)).all()
        applications = [app.to_response_model() for app in applications]
        return applications


@get(path="/commands", media_type=MediaType.JSON)
async def retrieve_commands() -> list[sql_models_NEW_v2.CommandSpecWithParameters]:
    model_cls = sql_models_NEW_v2.CommandSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, name=name, version=version)

    with settings.db.get_session() as session:
        # commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        commands = session.scalars(select(model_cls)).all()
        commands = [cmd.to_response_model() for cmd in commands]
        return commands


# async def _invoke_command_impl(cmd: sql_models.CommandInvocationCreate, broker: RabbitBroker):
#     msg = msg_specs.InvokeCommand(payload=cmd)
#
#     try:
#         # send command invocation request to any available clients
#         await broker.publish(
#             msg,
#             settings.rabbitmq.routing_key_qcrbox_registry,
#             rpc=False,
#             # raise_timeout=True,
#             # rpc_timeout=settings.rabbitmq.rpc_timeout,
#         )
#     except (TimeoutError, asyncio.exceptions.CancelledError) as exc:
#         # raise TimeoutError(f"{exc}")
#         raise HTTPException(f"{exc}")


# async def _invoke_command_impl_via_nats(cmd: sql_models.CommandInvocationCreate, nats_broker: NatsBroker):
#     msg = msg_specs.InvokeCommand(payload=cmd)
#
#     try:
#         # send command invocation request to any available clients
#         await nats_broker.publish(
#             msg,
#             f"cmd-invocation.request.{msg.payload.nats_subject}",
#             rpc=True,
#             raise_timeout=True,
#             rpc_timeout=settings.nats.rpc_timeout,
#         )
#     except TimeoutError:
#         raise ServiceUnavailableException("No clients available to execute command.")


def verify_command_exists(
    application_slug: str, application_version: str | None, command_name: str | None
) -> sql_models_NEW_v2.CommandSpecDB:
    with settings.db.get_session() as session:
        try:
            cmd_spec_db = session.exec(
                select(sql_models_NEW_v2.CommandSpecDB)
                .join(sql_models_NEW_v2.ApplicationSpecDB)
                .options(joinedload(sql_models_NEW_v2.CommandSpecDB.application))
                .where(
                    application_slug is None or (sql_models_NEW_v2.ApplicationSpecDB.slug == application_slug),
                    application_version is None or (sql_models_NEW_v2.ApplicationSpecDB.version == application_version),
                    sql_models_NEW_v2.CommandSpecDB.name == command_name,
                )
            ).one()
        except sqlalchemy.exc.NoResultFound:
            error_msg = (
                f"Command not found: {command_name} "
                f"(application: {application_slug!r}, "
                f"version: {application_version!r})"
            )
            logger.error(error_msg)
            raise ClientException(error_msg)

    return cmd_spec_db


def validate_arguments_against_command_parameters(
    cmd_spec_db: sql_models_NEW_v2.CommandSpecDB, arguments: dict
) -> None:
    params = list(cmd_spec_db.parameters.values())
    required_param_names = set(p["name"] for p in params if p["required"] is True)
    all_param_names = set(cmd_spec_db.parameters.keys())
    arg_names = set(arguments.keys())

    if not required_param_names.issubset(arg_names):
        params_not_supplied = required_param_names.difference(arg_names)
        missing_args = ", ".join(repr(name) for name in params_not_supplied)
        error_msg = f"The following required arguments are missing: {missing_args}"
        logger.error(error_msg)
        raise ClientException(error_msg)

    if not arg_names.issubset(all_param_names):
        invalid_args = arg_names.difference(all_param_names)
        invalid_args_str = ", ".join(repr(name) for name in invalid_args)
        error_msg = f"Invalid arguments: {invalid_args_str}"
        logger.error(error_msg)
        raise ClientException(error_msg)


@post(path="/commands/invoke", media_type=MediaType.JSON)
async def commands_invoke(data: sql_models_NEW_v2.CommandInvocationCreate) -> dict:
    logger.info(f"Received command invocation via API: {data=}")

    with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
        nats_broker = await con.aget(NatsBroker)

    cmd_spec_db = verify_command_exists(data.application_slug, data.application_version, data.command_name)
    validate_arguments_against_command_parameters(cmd_spec_db, data.arguments)

    msg = msg_specs.InvokeCommandNATS(
        application_slug=cmd_spec_db.application.slug,
        application_version=cmd_spec_db.application.version,
        command_name=cmd_spec_db.name,
        arguments=data.arguments,
    )

    response_json = await nats_broker.publish(msg, "server.cmd.handle_command_invocation_by_user", rpc=True)
    response = msg_specs.QCrBoxGenericResponse(**response_json)
    if response.status == msg_specs.ResponseStatusEnum.ERROR:
        raise ClientException(detail=response.msg, extra=response.payload)

    return dict(
        msg="Accepted command invocation request",
        status="ok",
        payload={
            "calculation_id": response.payload.calculation_id,
        },
    )


# @post(path="/commands/invoke_OLD", media_type=MediaType.JSON)
# async def commands_invoke_OLD(data: sql_models.CommandInvocationCreate) -> dict:
#     logger.info(f"[DDD] Received {data=}")
#
#     with svcs.Container(QCRBOX_SVCS_REGISTRY) as con:
#         # broker = await con.aget(RabbitBroker)
#         nats_broker = await con.aget(NatsBroker)
#
#     # await _invoke_command_impl(data, broker)
#     # await _invoke_command_impl_via_nats(data, broker)
#     msg = msg_specs.CommandInvocationRequest(payload=data)
#
#     client_response_event = anyio.Event()
#     reply_subject = f"cmd-invocation.response.{msg.payload.correlation_id}"
#
#     await nats_broker.close()
#
#     @nats_broker.subscriber(reply_subject, filter=lambda msg: msg.content_type == "")
#     async def discard_spurious_empty_messages(msg: bytes):
#         logger.warning(
#             f"Discarding spurious empty message: {msg} (this seems to be "
#             f"a FastStream bug, but it should not cause any issues)."
#         )
#
#     @nats_broker.subscriber(reply_subject, filter=lambda msg: msg.content_type != "")
#     async def handle_client_response(response_msg: dict):
#         logger.debug(f"Received response from client: {response_msg}")
#         if not client_response_event.is_set():
#             client_response_event.set()
#             return "All systems go!"
#         else:
#             return "Better luck next time."
#
#     await nats_broker.start()
#
#     # send command invocation request to any available clients
#
#     my_publish_func = functools.partial(
#         nats_broker.publish,
#         subject=f"cmd-invocation.request.{msg.payload.nats_subject}",
#         reply_to=reply_subject,
#     )
#
#     async with anyio.create_task_group() as tg:
#         with anyio.move_on_after(settings.nats.rpc_timeout):
#             tg.start_soon(my_publish_func, msg)
#             # tg.start_soon(client_response_event.wait)
#             await client_response_event.wait()
#
#     if not client_response_event.is_set():
#         logger.debug("No client responded within the timeout.")
#         raise ServiceUnavailableException("No client available to execute command.")
#
#     return dict(
#         msg="Accepted command invocation request",
#         status="ok",
#         payload={
#             "correlation_id": data.correlation_id,
#         },
#     )


@get(path="/calculations/{calculation_id:str}", media_type=MediaType.JSON)
async def get_calculation_info_by_calculation_id(calculation_id: str) -> dict | Response[dict]:
    # with settings.db.get_session() as session:
    #     try:
    #         calc = session.exec(
    #             select(sql_models.CalculationDB).where(sql_models.CalculationDB.calculation_id == calculation_id)
    #         ).one()
    #         pass
    #     except sqlalchemy.orm.exc.NoResultFound:
    #         return Response(
    #             {"msg": f"No calculation exists with id={calculation_id}"},
    #             status_code=404)

    try:
        kv_calculation_status = await get_nats_key_value(bucket="calculation_status")
        calc_status_info = (await kv_calculation_status.get(calculation_id)).value
        return json.loads(calc_status_info)
    except nats.js.errors.KeyNotFoundError:
        return Response({"status": "error", "msg": f"Calculation not found: {calculation_id!r}"}, status_code=404)


@get(path="/calculations", media_type=MediaType.JSON)
async def get_calculation_info() -> list[dict]:
    with settings.db.get_session() as session:
        calculations_db = session.exec(select(sql_models_NEW_v2.CalculationDB)).all()
        return [c.to_response_model() for c in calculations_db]


def create_server_asgi_server(custom_lifespan) -> Litestar:
    app = Litestar(
        route_handlers=[
            hello,
            health_check,
            retrieve_applications,
            retrieve_commands,
            commands_invoke,
            get_calculation_info,
            get_calculation_info_by_calculation_id,
        ],
        lifespan=[custom_lifespan],
        debug=True,
        plugins=[StructlogPlugin()],
        openapi_config=OpenAPIConfig(title="QCrBox Server API", version="0.1"),
    )
    return app
