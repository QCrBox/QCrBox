from typing import Annotated, Any

import sqlalchemy.exc
from litestar import MediaType, Request, Response, Router, get, post

__all__ = ["api_router"]

from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body

from pyqcrbox import logger, msg_specs, sql_models
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


@get(path="/commands/{cmd_id:int}", media_type=MediaType.JSON)
async def retrieve_command_by_id(cmd_id: int) -> sql_models.CommandSpecWithParameters | Response[dict]:
    try:
        return api_helpers._retrieve_command_by_id(cmd_id)
    except sqlalchemy.exc.NoResultFound:
        return Response({"status": "error", "msg": f"Command not found: id={cmd_id!r}"}, status_code=404)


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
    return await api_helpers._get_data_files()


async def _get_data_files() -> list[dict]:
    data_file_manager = await get_data_file_manager()
    data_files = await data_file_manager.get_data_files()
    return [f.to_response_model() for f in data_files]


@post(path="/commands/invoke", media_type=MediaType.JSON)
async def commands_invoke(data: sql_models.CommandInvocationCreate, request: Request) -> dict:
    logger.info(f"Received command invocation via API: {data=}")

    response_json = await api_helpers._invoke_command(data)
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
        retrieve_command_by_id,
        commands_invoke,
        get_calculation_info,
        get_calculation_info_by_calculation_id,
        get_data_files,
        handle_data_file_upload,
    ],
)
