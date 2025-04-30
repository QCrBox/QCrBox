from typing import Annotated

import sqlalchemy.exc
from litestar import MediaType, Router, delete, get, post

__all__ = ["api_router"]

from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import eel_logging
from pyqcrbox.registry.shared.qcrbox_response import QCrBoxResponse

from . import api_helpers


@delete(path="/datasets/delete/{dataset_id:str}")
@eel_logging
async def delete_datasets_delete_by_dataset_id(dataset_id: str) -> None:
    await api_helpers.delete_dataset(dataset_id)


@get(path="/applications", media_type=MediaType.JSON)
@eel_logging
async def get_applications() -> QCrBoxResponse:
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


@get(path="/calculations", media_type=MediaType.JSON)
@eel_logging
async def get_calculations() -> QCrBoxResponse:
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


@get(path="/calculations/{calculation_id:str}", media_type=MediaType.JSON)
@eel_logging
async def get_calculations_by_calculation_id(calculation_id: str) -> QCrBoxResponse:
    try:
        calculations = await api_helpers.get_calculation_info_by_calculation_id(calculation_id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved calculation: {calculation_id!r}",
                "data": {
                    "calculation_id": calculation_id,
                    "calculations": calculations,
                },
            },
            status_code=200,
        )
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


@get(path="/commands", media_type=MediaType.JSON)
@eel_logging
async def get_commands() -> QCrBoxResponse:
    _commands = api_helpers.retrieve_commands()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved commands",
            "data": {
                "commands": _commands,
            },
        },
        status_code=200,
    )


@get(path="/commands/{cmd_id:int}", media_type=MediaType.JSON)
@eel_logging
async def get_commands_by_cmd_id(cmd_id: int) -> QCrBoxResponse:
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


@get(path="/data_files", media_type=MediaType.JSON)
@eel_logging
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
@eel_logging
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


@get(path="/datasets/{dataset_id:str}", media_type=MediaType.JSON)
@eel_logging
async def get_datasets_by_dataset_id(dataset_id: str) -> QCrBoxResponse:
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
                "error": {
                    "code": 404,
                    "message": f"Dataset not found: {dataset_id!r}",
                },
            },
            status_code=404,
        )


@get(path="/healthz", media_type=MediaType.JSON)
@eel_logging
async def healthz() -> QCrBoxResponse:
    return QCrBoxResponse(
        {
            "status": "ok",
        },
        status_code=200,
    )


@get("/", media_type=MediaType.JSON, include_in_schema=False)
@eel_logging
async def index() -> QCrBoxResponse:
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Hello from QCrBox!",
        },
        status_code=200,
    )


# @post(path="/commands/invoke", media_type=MediaType.JSON)
# @eel_logging
# async def post_commands_invoke(data: sql_models.CommandInvocationCreate, request: Request) -> QCrBoxResponse:
#     logger.info(f"Received command invocation via API: {data=}")
#
#     response_json = await api_helpers.invoke_command(data)
#     response = msg_specs.QCrBoxGenericQCrBoxResponse(**response_json)
#
#     if response.status == msg_specs.QCrBoxResponseStatusEnum.ERROR:
#         raise ClientException(detail=response.msg, extra=response.payload)
#
#     return QCrBoxResponse(
#         {
#             "status": "success",
#             "message": f"Command invocation accepted: {data.command_name!r}",
#             "data": {
#                 "calculation_id": response.payload.calculation_id,
#                 "href": request.url_for("get_calculation_details", calculation_id=response.payload.calculation_id),
#             },
#         },
#         status_code=200,
#     )


@post(path="/data_files/upload", media_type=MediaType.JSON)
@eel_logging
async def post_data_files_upload(
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


@post(path="/datasets/upload", media_type=MediaType.JSON)
@eel_logging
async def post_datasets_upload(
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


api_router = Router(
    path="/api",
    route_handlers=[
        delete_datasets_delete_by_dataset_id,
        get_applications,
        get_calculations,
        get_calculations_by_calculation_id,
        get_commands,
        get_commands_by_cmd_id,
        get_data_files,
        get_datasets,
        get_datasets_by_dataset_id,
        healthz,
        index,
        # post_commands_invoke,
        post_data_files_upload,
        post_datasets_upload,
    ],
)
