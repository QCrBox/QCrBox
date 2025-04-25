from typing import Annotated, Any

import sqlalchemy.exc
from litestar import MediaType, Request, Response, Router, delete, get, post

__all__ = ["api_router"]

from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.data_management import DatasetResponse
from pyqcrbox.data_management.data_file import DataFileMetadataResponse
from pyqcrbox.debug import log_entry_exit

from . import api_helpers


@get("/", media_type=MediaType.JSON, include_in_schema=False)
@log_entry_exit
async def api_root_handler() -> dict[str, Any]:
    return {"message": "Hello from QCrBox!"}


@get(path="/healthz", media_type=MediaType.JSON, skip_logging=False)
@log_entry_exit
async def health_check() -> dict:
    return {"status": "ok"}


@get(path="/applications", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_applications(
    # slug: str | None = None, version: str | None = None
) -> list[sql_models.ApplicationSpecWithCommands]:
    return api_helpers.retrieve_applications()


@get(path="/commands", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_commands(
    # name: str | None, application_slug: str | None, application_version: str | None
) -> list[sql_models.CommandSpecWithParameters]:
    return api_helpers.retrieve_commands()


@get(path="/commands/{cmd_id:int}", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_command_by_id(cmd_id: int) -> sql_models.CommandSpecWithParameters | Response[dict]:
    try:
        return api_helpers.retrieve_command_by_id(cmd_id)
    except sqlalchemy.exc.NoResultFound:
        return Response({"status": "error", "msg": f"Command not found: id={cmd_id!r}"}, status_code=404)


@get(path="/calculations", media_type=MediaType.JSON)
@log_entry_exit
async def get_calculation_info() -> list[sql_models.CalculationResponseModel]:
    return api_helpers.get_calculation_info()


@get(path="/calculations/{calculation_id:str}", media_type=MediaType.JSON, name="get_calculation_details")
@log_entry_exit
async def get_calculation_info_by_calculation_id(calculation_id: str) -> dict | Response[dict]:
    try:
        return await api_helpers.get_calculation_info_by_calculation_id(calculation_id)
    except api_helpers.CalculationNotFoundError:
        return Response({"status": "error", "msg": f"Calculation not found: {calculation_id!r}"}, status_code=404)


@post(path="/data_files/upload", media_type=MediaType.JSON)
@log_entry_exit
async def handle_data_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    qcrbox_data_file_id = await api_helpers.import_data_file(data)
    return Response(
        {
            "status": "success",
            "msg": f"Imported data file: {data.filename!r}",
            "payload": {"qcrbox_id": qcrbox_data_file_id},
        },
        status_code=200,
    )


@get(path="/data_files", media_type=MediaType.JSON)
@log_entry_exit
async def get_data_files() -> list[DataFileMetadataResponse]:
    return await api_helpers.get_data_files()


@get(path="/datasets", media_type=MediaType.JSON)
@log_entry_exit
async def get_datasets() -> list[DatasetResponse]:
    return await api_helpers.get_datasets()


@post(path="/datasets/upload", media_type=MediaType.JSON)
@log_entry_exit
async def handle_dataset_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    qcrbox_dataset_id = await api_helpers.import_dataset(data)
    return Response(
        {
            "status": "success",
            "msg": f"Imported dataset: {data.filename!r}",
            "payload": {"qcrbox_dataset_id": qcrbox_dataset_id},
        },
        status_code=200,
    )


@delete(path="/datasets/delete/{dataset_id:str}")
@log_entry_exit
async def handle_dataset_delete(dataset_id: str) -> None:
    await api_helpers.delete_dataset(dataset_id)


@post(path="/commands/invoke", media_type=MediaType.JSON)
@log_entry_exit
async def commands_invoke(data: sql_models.CommandInvocationCreate, request: Request) -> dict:
    logger.info(f"Received command invocation via API: {data=}")

    response_json = await api_helpers.invoke_command(data)
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
        get_datasets,
        handle_data_file_upload,
        handle_dataset_upload,
        handle_dataset_delete,
    ],
)
