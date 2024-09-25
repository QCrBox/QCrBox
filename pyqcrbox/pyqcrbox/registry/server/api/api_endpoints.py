from typing import Annotated, Any

import sqlalchemy
import svcs
from faststream.nats import NatsBroker
from litestar import MediaType, Request, Response, Router, get, post

__all__ = ["api_router"]

from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body
from sqlalchemy.orm import joinedload
from sqlmodel import select

from pyqcrbox import QCRBOX_SVCS_REGISTRY, logger, msg_specs, settings, sql_models
from pyqcrbox.services import get_data_file_manager

from . import api_helpers


@get("/", media_type=MediaType.JSON, include_in_schema=False)
async def api_root_handler() -> dict[str, Any]:
    return {"message": "Hello world!"}


@get(path="/healthz", media_type=MediaType.JSON, skip_logging=False)
async def health_check() -> dict:
    return {"status": "ok"}


@get(path="/applications", media_type=MediaType.JSON)
async def retrieve_applications(
    # slug: str | None = None, version: str | None = None
) -> list[sql_models.ApplicationSpecWithCommands]:
    return api_helpers._retrieve_applications()


@get(path="/commands", media_type=MediaType.JSON)
async def retrieve_commands(
    # name: str | None, application_slug: str | None, application_version: str | None
) -> list[sql_models.CommandSpecWithParameters]:
    return api_helpers._retrieve_commands()


@get(path="/calculations", media_type=MediaType.JSON)
async def get_calculation_info() -> list[sql_models.CalculationResponseModel]:
    return api_helpers._get_calculation_info()


@get(path="/calculations/{calculation_id:str}", media_type=MediaType.JSON, name="get_calculation_details")
async def get_calculation_info_by_calculation_id(calculation_id: str) -> dict | Response[dict]:
    try:
        return await api_helpers._get_calculation_info_by_calculation_id(calculation_id)
    except api_helpers.CalculationNotFoundError:
        return Response({"status": "error", "msg": f"Calculation not found: {calculation_id!r}"}, status_code=404)


@post(path="/data_files/upload", media_type=MediaType.TEXT)
async def handle_data_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> str:
    # data_file_manager = await get_data_file_manager()
    filename = data.filename
    logger.debug(f"Storing data file in Nats object store: {filename!r}")
    # qcrbox_data_file_id = await data_file_manager.import_bytes(await data.read(), filename=filename)
    # return f"Successfully imported data file: {filename!r} (<code>{qcrbox_data_file_id!r}</code>)"
    return f"<li>{filename}</li>"


@get(path="/data_files", media_type=MediaType.JSON)
async def get_data_files() -> list[dict]:
    return await _get_data_files()


async def _get_data_files() -> list[dict]:
    data_file_manager = await get_data_file_manager()
    data_files = await data_file_manager.get_data_files()
    return [f.to_response_model() for f in data_files]


def verify_command_exists(
    application_slug: str, application_version: str | None, command_name: str | None
) -> sql_models.CommandSpecDB:
    with settings.db.get_session() as session:
        try:
            cmd_spec_db = session.exec(
                select(sql_models.CommandSpecDB)
                .join(sql_models.ApplicationSpecDB)
                .options(joinedload(sql_models.CommandSpecDB.application))
                .where(
                    application_slug is None or (sql_models.ApplicationSpecDB.slug == application_slug),
                    application_version is None or (sql_models.ApplicationSpecDB.version == application_version),
                    sql_models.CommandSpecDB.name == command_name,
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
        except sqlalchemy.exc.MultipleResultsFound:
            error_msg = (
                f"Found multiple candidates for command: {command_name}. "
                f"Please supply the application's slug (and version if needed) "
                f"to disambiguate between the matching commands."
            )
            logger.error(error_msg)
            raise ClientException(error_msg)

    return cmd_spec_db


def validate_arguments_against_command_parameters(cmd_spec_db: sql_models.CommandSpecDB, arguments: dict) -> None:
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
async def commands_invoke(data: sql_models.CommandInvocationCreate, request: Request) -> dict:
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
            "href": request.url_for("get_calculation_details", calculation_id=response.payload.calculation_id),
        },
    )


api_router = Router(
    path="/api",
    route_handlers=[
        api_root_handler,
        health_check,
        retrieve_applications,
        retrieve_commands,
        commands_invoke,
        get_calculation_info,
        get_calculation_info_by_calculation_id,
        get_data_files,
        handle_data_file_upload,
    ],
)
