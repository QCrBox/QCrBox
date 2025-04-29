from typing import Annotated

import sqlalchemy.exc
from litestar import MediaType, Request, Router, delete, get, post

__all__ = ["api_router"]

from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException
from litestar.params import Body

from pyqcrbox import logger, msg_specs, sql_models
from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import log_entry_exit
from pyqcrbox.registry.shared.qcrbox_response import QCrBoxResponse

from . import api_helpers


@get("/", media_type=MediaType.JSON, include_in_schema=False)
@log_entry_exit
async def api_root_handler() -> QCrBoxResponse:
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Hello from QCrBox!",
        },
        status_code=200,
    )


@get(path="/healthz", media_type=MediaType.JSON, skip_logging=False)
@log_entry_exit
async def health_check() -> QCrBoxResponse:
    return QCrBoxResponse(
        {
            "status": "ok",
        },
        status_code=200,
    )


@get(path="/applications", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_applications() -> QCrBoxResponse:
    applications = api_helpers.retrieve_applications()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved applications",
            "data": {
                "applications": applications,
            },
        },
        status_code=200,
    )


@get(path="/commands", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_commands() -> QCrBoxResponse:
    commands = api_helpers.retrieve_commands()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved commands",
            "data": {
                "commands": commands,
            },
        },
        status_code=200,
    )


@get(path="/commands/{cmd_id:int}", media_type=MediaType.JSON)
@log_entry_exit
async def retrieve_command_by_id(cmd_id: int) -> QCrBoxResponse:
    try:
        command = api_helpers.retrieve_command_by_id(cmd_id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved command: {cmd_id!r}",
                "data": {
                    "command_id": cmd_id,
                    "command": command,
                },
            },
            status_code=200,
        )
    except sqlalchemy.exc.NoResultFound:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Command not found: id={cmd_id!r}",
                },
            },
            status_code=404,
        )


@get(path="/calculations", media_type=MediaType.JSON)
@log_entry_exit
async def get_calculation_info() -> QCrBoxResponse:
    calculations = api_helpers.get_calculation_info()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved calculations",
            "data": {
                "calculations": calculations,
            },
        },
        status_code=200,
    )


@get(path="/calculations/{calculation_id:str}", media_type=MediaType.JSON, name="get_calculation_details")
@log_entry_exit
async def get_calculation_info_by_calculation_id(calculation_id: str) -> QCrBoxResponse:
    try:
        return await api_helpers.get_calculation_info_by_calculation_id(calculation_id)
    except api_helpers.CalculationNotFoundError:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Calculation not found: {calculation_id!r}",
                },
            },
            status_code=404,
        )


@post(path="/data_files/upload", media_type=MediaType.JSON)
@log_entry_exit
async def handle_data_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> QCrBoxResponse:
    qcrbox_data_file_id = await api_helpers.import_data_file(data)
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Imported data file: {data.filename!r}",
            "data": {
                "qcrbox_id": qcrbox_data_file_id,
            },
        },
        status_code=200,
    )


@get(path="/data_files", media_type=MediaType.JSON)
@log_entry_exit
async def get_data_files() -> QCrBoxResponse:
    data_files = await api_helpers.get_data_files()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved data files",
            "data": {
                "data_files": data_files,
            },
        },
        status_code=200,
    )


@get(path="/datasets", media_type=MediaType.JSON)
@log_entry_exit
async def get_datasets() -> QCrBoxResponse:
    datasets = await api_helpers.get_datasets()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved datasets",
            "data": {
                "datasets": datasets,
            },
        },
        status_code=200,
    )


@post(path="/datasets/upload", media_type=MediaType.JSON)
@log_entry_exit
async def handle_dataset_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> QCrBoxResponse:
    qcrbox_dataset_id = await api_helpers.import_dataset(data)
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Imported dataset: {data.filename!r}",
            "data": {
                "qcrbox_dataset_id": qcrbox_dataset_id,
            },
        },
        status_code=200,
    )


@delete(path="/datasets/delete/{dataset_id:str}")
@log_entry_exit
async def handle_dataset_delete(dataset_id: str) -> None | QCrBoxResponse:
    try:
        await api_helpers.delete_dataset(dataset_id)
    except (KeyError, DatasetNotFoundError):
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Dataset not found: {dataset_id!r}",
                },
            },
            status_code=404,
        )


@get(path="/datasets/{dataset_id:str}", media_type=MediaType.JSON)
@log_entry_exit
async def handle_get_dataset_by_dataset_id(dataset_id: str) -> QCrBoxResponse:
    try:
        dataset = await api_helpers.get_dataset_info(dataset_id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved dataset: {dataset_id!r}",
                "data": dataset,
            },
            status_code=200,
        )
    except DatasetNotFoundError:
        return QCrBoxResponse(
            {
                "status": "error",
                "message": f"Dataset not found: {dataset_id!r}",
            },
            status_code=404,
        )


@post(path="/commands/invoke", media_type=MediaType.JSON)
@log_entry_exit
async def commands_invoke(data: sql_models.CommandInvocationCreate, request: Request) -> QCrBoxResponse:
    logger.info(f"Received command invocation via API: {data=}")

    response_json = await api_helpers.invoke_command(data)
    response = msg_specs.QCrBoxGenericQCrBoxResponse(**response_json)

    if response.status == msg_specs.QCrBoxResponseStatusEnum.ERROR:
        raise ClientException(detail=response.msg, extra=response.payload)

    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Command invocation accepted: {data.command_name!r}",
            "data": {
                "calculation_id": response.payload.calculation_id,
                "href": request.url_for("get_calculation_details", calculation_id=response.payload.calculation_id),
            },
        },
        status_code=200,
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
        handle_get_dataset_by_dataset_id,
    ],
)
