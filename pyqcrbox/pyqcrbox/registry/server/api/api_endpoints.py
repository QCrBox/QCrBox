"""
Organised API routes for QCrBox, grouped by resource.
"""

from typing import Annotated

import sqlalchemy.exc
from litestar import MediaType, Router, delete, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import Body, Parameter
from pydantic import BaseModel

from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import eel_logging
from pyqcrbox.registry.shared.qcrbox_response import (
    ApplicationsResponse,
    CalculationsResponse,
    QCrBoxResponse,
    QCrBoxResponseSpec,
)
from pyqcrbox.sql_models import CommandInvocationCreate

from . import api_helpers

__all__ = ["api_router"]


class InteractiveSessionCreate(BaseModel):
    application_slug: str
    application_version: str
    data_file_id: str


# ----- Dataset Endpoints -----
@delete(
    path="/datasets/{id:str}",
    description="Removes a dataset, of the given ID, and all of its associated data files from the QCrBox datastore.",
)
@eel_logging
async def delete_dataset_by_id(
    id: str = Parameter(title="Dataset ID", description="The ID of the dataset to delete."),
) -> None:
    await api_helpers.delete_dataset(id)


@get(path="/datasets", media_type=MediaType.JSON, summary="List all datasets")
@eel_logging
async def list_datasets() -> QCrBoxResponse:
    datasets = await api_helpers.get_datasets()
    return QCrBoxResponse(
        {"status": "success", "message": "Retrieved datasets", "payload": {"datasets": datasets}},
        status_code=200,
    )


@get(path="/datasets/{id:str}", media_type=MediaType.JSON, summary="Get dataset by ID")
@eel_logging
async def get_dataset_by_id(id: str) -> QCrBoxResponse:
    try:
        dataset = await api_helpers.get_dataset_info(id)
        return QCrBoxResponse(
            {"status": "success", "message": f"Retrieved dataset: {id!r}", "payload": dataset},
            status_code=200,
        )
    except DatasetNotFoundError:
        return QCrBoxResponse(
            {"status": "error", "error": {"code": 404, "message": f"Dataset not found: {id!r}"}},
            status_code=404,
        )


@post(path="/datasets", media_type=MediaType.JSON, summary="Create a new dataset")
@eel_logging
async def create_dataset(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> QCrBoxResponse:
    qcrbox_dataset_id = await api_helpers.import_dataset(data)
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Imported dataset: {data.filename!r}",
            "payload": {"qcrbox_dataset_id": qcrbox_dataset_id},
        },
        status_code=200,
    )


# ----- Data-File Endpoints -----
@get(path="/data-files", media_type=MediaType.JSON, summary="List all data files")
@eel_logging
async def list_data_files() -> QCrBoxResponse:
    data_files = await api_helpers.get_data_files()
    return QCrBoxResponse(
        {"status": "success", "message": "Retrieved data files", "payload": {"data_files": data_files}},
        status_code=200,
    )


@post(path="/data-files", media_type=MediaType.JSON, summary="Upload a data file")
@eel_logging
async def create_data_file(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> QCrBoxResponse:
    qcrbox_data_file_id = await api_helpers.import_data_file(data)
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Imported data file: {data.filename!r}",
            "payload": {"qcrbox_id": qcrbox_data_file_id},
        },
        status_code=200,
    )


# ----- Application Endpoints -----
@get(
    path="/applications",
    media_type=MediaType.JSON,
    summary="Get the registered applications",
    responses={
        200: ResponseSpec(
            data_container=QCrBoxResponseSpec[ApplicationsResponse], description="Successfully retrieved applications"
        )
    },
)
@eel_logging
async def list_applications() -> QCrBoxResponse:
    apps = api_helpers.retrieve_applications()
    return QCrBoxResponse(
        {"status": "success", "message": f"Retrieved {len(apps)} applications.", "payload": {"applications": apps}},
        status_code=200,
    )


# ----- Calculation Endpoints -----
@get(
    path="/calculations",
    media_type=MediaType.JSON,
    summary="Retrieve all calculations",
    responses={
        200: ResponseSpec(
            data_container=QCrBoxResponseSpec[CalculationsResponse], description="Successfully retrieved calculations"
        )
    },
)
@eel_logging
async def list_calculations() -> QCrBoxResponse:
    calcs = api_helpers.get_calculation_info()
    return QCrBoxResponse(
        {"status": "success", "message": "Retrieved calculations", "payload": {"calculations": calcs}},
        status_code=200,
    )


@get(path="/calculations/{id:str}", media_type=MediaType.JSON, summary="Get calculation by ID")
@eel_logging
async def get_calculation_by_id(id: str) -> QCrBoxResponse:
    try:
        calcs = await api_helpers.get_calculation_info_by_calculation_id(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved calculation: {id!r}",
                "payload": {"calculation_id": id, "calculations": calcs},
            },
            status_code=200,
        )
    except api_helpers.CalculationNotFoundError:
        return QCrBoxResponse(
            {"status": "error", "error": {"code": 404, "message": f"Calculation not found: {id!r}"}},
            status_code=404,
        )


# ----- Command Endpoints -----
@get(path="/commands", media_type=MediaType.JSON, summary="List all commands")
@eel_logging
async def list_commands() -> QCrBoxResponse:
    cmds = api_helpers.retrieve_commands()
    return QCrBoxResponse(
        {"status": "success", "message": "Retrieved commands", "payload": {"commands": cmds}},
        status_code=200,
    )


@get(path="/commands/{id:int}", media_type=MediaType.JSON, summary="Get command by ID")
@eel_logging
async def get_command_by_id(id: int) -> QCrBoxResponse:
    try:
        cmd = api_helpers.retrieve_command_by_id(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved command: {id!r}",
                "payload": {"command_id": id, "command": cmd},
            },
            status_code=200,
        )
    except sqlalchemy.exc.NoResultFound:
        return QCrBoxResponse(
            {"status": "error", "error": {"code": 404, "message": f"Command not found: id={id!r}"}},
            status_code=404,
        )


# ----- Interactive Session Endpoints -----


@get(path="/interactive-sessions", media_type=MediaType.JSON, summary="List interactive sessions")
@eel_logging
async def list_interactive_sessions() -> QCrBoxResponse:
    mgr = await api_helpers.get_data_file_manager()
    sessions = await mgr.get_interactive_sessions()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved interactive sessions",
            "payload": {"interactive_sessions": sessions},
        },
        status_code=200,
    )


@get(path="/interactive-sessions/{id:str}", media_type=MediaType.JSON, summary="Get interactive session by ID")
@eel_logging
async def get_interactive_session_by_id(id: str) -> QCrBoxResponse:
    mgr = await api_helpers.get_data_file_manager()
    try:
        sess = await mgr.get_interactive_session_info(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved interactive session: {id!r}",
                "payload": {"interactive_session": sess},
            },
            status_code=200,
        )
    except DatasetNotFoundError:
        return QCrBoxResponse(
            {"status": "error", "error": {"code": 404, "message": f"Interactive session not found: {id!r}"}},
            status_code=404,
        )


@post(
    path="/interactive-sessions/create",
    media_type=MediaType.JSON,
    summary="Create interactive session",
)
@eel_logging
async def create_interactive_session(
    data: Annotated[InteractiveSessionCreate, Body()],
) -> QCrBoxResponse:
    cmd = CommandInvocationCreate(
        application_slug=data.application_slug,
        application_version=data.application_version,
        command_name="interactive_session",
        arguments={"input_file": {"data_file_id": data.data_file_id}},
    )
    response = await api_helpers.invoke_command(cmd)
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Command invocation accepted: {data.application_slug!r}-{data.application_version!r}",
            "payload": {"calculation_id": response["payload"]["calculation_id"]},
        },
        status_code=200,
    )


@post(path="/interactive-sessions/close/{id:str}", media_type=MediaType.JSON, summary="Close interactive session")
@eel_logging
async def close_interactive_session(id: str) -> QCrBoxResponse:
    try:
        response = await api_helpers.close_interactive_session(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Closed interactive session: {id!r}",
                "payload": {"calculation_id": response.session_id, "output_dataset_id": response.output_dataset_id},
            },
            status_code=200,
        )
    except KeyError:
        return QCrBoxResponse(
            {"status": "error", "error": {"code": 404, "message": f"Interactive session not found: {id!r}"}},
            status_code=404,
        )


# ----- Health & Root -----
@get(path="/healthz", media_type=MediaType.JSON, summary="Health check")
@eel_logging
async def healthz() -> QCrBoxResponse:
    return QCrBoxResponse({"status": "ok"}, status_code=200)


@get(path="/", media_type=MediaType.JSON, include_in_schema=False, summary="Root handler")
@eel_logging
async def index() -> QCrBoxResponse:
    return QCrBoxResponse({"status": "success", "message": "Hello from QCrBox!"}, status_code=200)


# ----- Router Aggregation -----
api_router = Router(
    path="/api",
    route_handlers=[
        # Datasets
        delete_dataset_by_id,
        list_datasets,
        get_dataset_by_id,
        create_dataset,
        # Data files
        list_data_files,
        create_data_file,
        # Applications
        list_applications,
        # Calculations
        list_calculations,
        get_calculation_by_id,
        # Commands
        list_commands,
        get_command_by_id,
        # Interactive sessions
        list_interactive_sessions,
        get_interactive_session_by_id,
        create_interactive_session,
        close_interactive_session,
        # Health & Root
        healthz,
        index,
    ],
)
