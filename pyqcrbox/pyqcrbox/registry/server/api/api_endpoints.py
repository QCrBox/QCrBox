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
from pyqcrbox.sql_models import CommandInvocationCreate

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
            "payload": {
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
            "payload": {
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
                "payload": {
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
            "payload": {
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
                "payload": {
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
            "payload": {
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
            "payload": {
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
                "payload": dataset,
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


@get(path="/interactive_sessions", media_type=MediaType.JSON)
@eel_logging
async def get_interactive_sessions() -> QCrBoxResponse:
    data_file_manager = await api_helpers.get_data_file_manager()
    interactive_sessions = await data_file_manager.get_interactive_sessions()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved interactive sessions",
            "payload": {
                "interactive_sessions": interactive_sessions,
            },
        },
        status_code=200,
    )


@get(path="/interactive_sessions/{session_id:str}", media_type=MediaType.JSON)
@eel_logging
async def get_interactive_sessions_by_session_id(session_id: str) -> QCrBoxResponse:
    data_file_manager = await api_helpers.get_data_file_manager()
    try:
        interactive_session = await data_file_manager.get_interactive_session_info(session_id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved interactive session: {session_id!r}",
                "payload": {
                    "interactive_session": interactive_session,
                },
            },
            status_code=200,
        )
    except DatasetNotFoundError:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Interactive session not found: {session_id!r}",
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


@post(path="/commands/interactive/close")
@eel_logging
async def post_commands_interactive_session_close(interactive_session_id: str) -> QCrBoxResponse:
    try:
        response = await api_helpers.close_interactive_session(interactive_session_id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Closed interactive session: {interactive_session_id!r}",
                "payload": {
                    "calculation_id": response.session_id,
                    "output_dataset_id": response.output_dataset_id,
                },
            },
            status_code=200,
        )
    except KeyError:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Interactive session not found: {interactive_session_id!r}",
                },
            },
            status_code=404,
        )


@post(path="/commands/interactive/open", media_type=MediaType.JSON)
@eel_logging
async def post_commands_interactive_session_open(
    application_slug: str, application_version: str, data_file_id: str
) -> QCrBoxResponse:
    command = CommandInvocationCreate(
        application_slug=application_slug,
        application_version=application_version,
        command_name="interactive_session",
        arguments={"input_file": {"data_file_id": data_file_id}},
    )
    command_response = await api_helpers.invoke_command(command)
    interactive_session_id = command_response["payload"]["calculation_id"]

    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Command invocation accepted: {application_slug!r}-{application_version!r}",
            "payload": {
                "calculation_id": interactive_session_id,
            },
        },
        status_code=200,
    )


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
            "payload": {
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
            "payload": {
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
        get_interactive_sessions,
        get_interactive_sessions_by_session_id,
        healthz,
        index,
        post_commands_interactive_session_close,
        post_commands_interactive_session_open,
        post_data_files_upload,
        post_datasets_upload,
    ],
)
