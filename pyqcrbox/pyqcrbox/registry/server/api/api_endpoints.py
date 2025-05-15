"""
Organised API routes for QCrBox, grouped by resource.
"""

from typing import Annotated

import sqlalchemy.exc
from litestar import MediaType, Request, Router, delete, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body, Parameter
from litestar.response import Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from pydantic import BaseModel

from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import eel_logging
from pyqcrbox.registry.server.api import api_schema as schema
from pyqcrbox.registry.shared.qcrbox_response import QCrBoxResponse
from pyqcrbox.sql_models import CalculationStatusEnum, CommandInvocationCreate

from . import api_helpers

__all__ = ["api_router"]


class InteractiveSessionCreateWithDataFileData(BaseModel):
    application_slug: str
    application_version: str
    data_file_id: str


class QCrBoxAPIException(HTTPException):
    pass


# Datasets -------------------------------------------------------------------------------------------------------------


@delete(path="/datasets/{id:str}", summary="Delete a dataset")
@eel_logging
async def delete_dataset_by_id(id: str = Parameter(title="Dataset ID")) -> None:
    """Remove a dataset and associated data files from the data store."""
    await api_helpers.delete_dataset(id)


@get(path="/datasets", media_type=MediaType.JSON, summary="List all datasets")
@eel_logging
async def list_datasets() -> schema.QCrBoxResponse[list[schema.DatasetsResponse]]:
    """Retrieve a list of all datasets in the data store."""
    datasets = await api_helpers.get_datasets()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": "Retrieved datasets",
            "payload": {
                "datasets": datasets,
            },
        },
        status_code=200,
    )


@get(path="/datasets/{id:str}", media_type=MediaType.JSON, summary="Get dataset by ID")
@eel_logging
async def get_dataset_by_id(
    id: str = Parameter(title="Dataset ID"),
) -> schema.QCrBoxResponse[list[schema.DatasetsResponse]]:
    """Retrieve a dataset by its ID, including metadata of linked data files."""
    try:
        dataset = await api_helpers.get_dataset_info(id)
        return QCrBoxResponse(
            content={
                "status": "success",
                "message": f"Retrieved dataset: {id!r}",
                "payload": {
                    "datasets": [dataset],
                },
            },
            status_code=200,
        )
    except (KeyError, DatasetNotFoundError):
        raise QCrBoxAPIException(detail=f"Dataset not found: {id!r}", status_code=404)


@post(path="/datasets", media_type=MediaType.TEXT, summary="Create a new dataset")
@eel_logging
async def create_dataset(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART, title="The file contents to upload")],
) -> schema.QCrBoxResponse[schema.DatasetsResponse]:
    """Create a new dataset by uploading data files."""
    qcrbox_dataset_id = await api_helpers.import_dataset(data)
    dataset = await api_helpers.get_dataset_info(qcrbox_dataset_id)
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Created dataset: {qcrbox_dataset_id!r}",
            "payload": {
                "datasets": [dataset],
            },
        },
        status_code=201,
    )


@get(path="/datasets/{id:str}/download", media_type="application/octet-stream", summary="Download a dataset")
@eel_logging
async def download_dataset_by_id(id: str = Parameter(title="Dataset ID")) -> Response[bytes]:
    """Download the data files of a datast as a Zip file."""
    dataset_contents_as_bytes, output_filename = await api_helpers.export_dataset(id)
    return Response(
        content=dataset_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={output_filename!r}"},
        status_code=200,
    )


# Data files -----------------------------------------------------------------------------------------------------------


@get(path="/data-files", media_type=MediaType.JSON, summary="List all data files")
@eel_logging
async def list_data_files() -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Retrieve a list of all data files in the data store."""
    data_files = await api_helpers.get_data_files()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": "Retrieved data files",
            "payload": {
                "data_files": data_files,
            },
        },
        status_code=200,
    )


@get(path="/data-files/{id:str}", media_type=MediaType.JSON, summary="Get a data file")
@eel_logging
async def get_data_file_by_id(
    id: str = Parameter(title="Data file ID"),
) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Retrieve a data files by it's ID."""
    try:
        data_file = await api_helpers.get_data_file_info(id)
        return QCrBoxResponse(
            content={
                "status": "success",
                "message": f"Retrieved data file: {id!r}",
                "payload": {
                    "data_files": [data_file],
                },
            },
            status_code=200,
        )
    except KeyError:
        raise QCrBoxAPIException(detail=f"Data file not found: {id!r}", status_code=404)


@post(path="/data-files", media_type=MediaType.TEXT, summary="Upload a data file")
@eel_logging
async def create_data_file(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART, title="The file to upload")],
) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Upload a new data file to the data store."""
    qcrbox_data_file_id = await api_helpers.import_data_file(data)
    data_file = await api_helpers.get_data_file_info(qcrbox_data_file_id)
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Imported data file: {data.filename!r}",
            "payload": {
                "data_files": [data_file],
            },
        },
        status_code=201,
    )


@get(path="/data-files/{id:str}/download", media_type="application/octet-stream", summary="Download a data file")
async def download_data_file_by_id(id: str = Parameter(title="Data file ID")) -> Response[bytes]:
    """Download a data file from the data store."""
    data_file_contents_as_bytes, data_file_name = await api_helpers.export_data_file(id)
    return Response(
        content=data_file_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={data_file_name!r}"},
    )


# Applications ---------------------------------------------------------------------------------------------------------


@get(
    path="/applications",
    media_type=MediaType.JSON,
    summary="Get the registered applications",
)
@eel_logging
async def list_applications() -> QCrBoxResponse:
    apps = api_helpers.retrieve_applications()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Retrieved {len(apps)} applications.",
            "payload": {"applications": apps},
        },
        status_code=200,
    )


# Calculations ---------------------------------------------------------------------------------------------------------


@get(
    path="/calculations",
    media_type=MediaType.JSON,
    summary="Retrieve all calculations",
)
@eel_logging
async def list_calculations() -> QCrBoxResponse:
    calcs = api_helpers.get_calculation_info()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved calculations",
            "payload": {"calculations": calcs},
        },
        status_code=200,
    )


@get(
    path="/calculations/{id:str}",
    media_type=MediaType.JSON,
    summary="Get calculation by ID",
)
@eel_logging
async def get_calculation_by_id(id: str) -> QCrBoxResponse:
    try:
        calculation = await api_helpers.get_calculation_info_by_calculation_id(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved calculation: {id!r}",
                "payload": {"calculation_id": id, "calculation": calculation},
            },
            status_code=200,
        )
    except api_helpers.CalculationNotFoundError:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {"code": 404, "message": f"Calculation not found: {id!r}"},
            },
            status_code=404,
        )


# Commands -------------------------------------------------------------------------------------------------------------


@get(path="/commands", media_type=MediaType.JSON, summary="List all commands")
@eel_logging
async def list_commands() -> QCrBoxResponse:
    cmds = api_helpers.retrieve_commands()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved commands",
            "payload": {"commands": cmds},
        },
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
            {
                "status": "error",
                "error": {"code": 404, "message": f"Command not found: id={id!r}"},
            },
            status_code=404,
        )


# Interactive sessions -------------------------------------------------------------------------------------------------


@get(
    path="/interactive-sessions",
    media_type=MediaType.JSON,
    summary="List interactive sessions",
)
@eel_logging
async def list_interactive_sessions() -> QCrBoxResponse:
    sessions = await api_helpers.get_interactive_sessions()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": "Retrieved interactive sessions",
            "payload": {"interactive_sessions": sessions},
        },
        status_code=200,
    )


@get(
    path="/interactive-sessions/{id:str}",
    media_type=MediaType.JSON,
    summary="Get interactive session by ID",
)
@eel_logging
async def get_interactive_session_by_id(id: str) -> QCrBoxResponse:
    try:
        session_info = await api_helpers.get_interactive_session_info(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved interactive session: {id!r}",
                "payload": {"interactive_session": session_info},
            },
            status_code=200,
        )
    except KeyError:
        return QCrBoxResponse(
            {
                "status": "error",
                "error": {
                    "code": 404,
                    "message": f"Interactive session not found: {id!r}",
                },
            },
            status_code=404,
        )


@post(
    path="/interactive-sessions",
    media_type=MediaType.JSON,
    summary="Create interactive session",
)
@eel_logging
async def create_interactive_session_with_data_file(
    data: Annotated[InteractiveSessionCreateWithDataFileData, Body()],
) -> QCrBoxResponse:
    # TODO: we should have the arguments/data_files be in the InteractiveSessionCreateWithDataFileData model instead
    command_spec = CommandInvocationCreate(
        application_slug=data.application_slug,
        application_version=data.application_version,
        command_name="interactive_session",
        arguments={"input_file": {"data_file_id": data.data_file_id}},
    )
    response = await api_helpers.invoke_command(command_spec)

    if response["status"] != CalculationStatusEnum.SUBMITTED:
        raise HTTPException(status_code=500, detail="Failed to create interactive session")

    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Command invocation accepted: {data.application_slug!r}-{data.application_version!r}",
            "payload": {"calculation_id": response["payload"]["calculation_id"]},
        },
        status_code=201,
    )


@delete(
    path="/interactive-sessions/{id:str}",
    media_type=MediaType.JSON,
    summary="Close interactive session",
)
@eel_logging
async def close_interactive_session(id: str) -> None:
    try:
        await api_helpers.close_interactive_session(id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Interactive session not found: {id!r}")


# Health and root ------------------------------------------------------------------------------------------------------


@get(path="/healthz", media_type=MediaType.JSON, summary="Health check")
@eel_logging
async def healthz() -> QCrBoxResponse:
    return QCrBoxResponse({"status": "ok"}, status_code=200)


@get(path="/", media_type=MediaType.JSON, summary="Root handler")
@eel_logging
async def index() -> QCrBoxResponse:
    return QCrBoxResponse({"status": "success", "message": "Hello from QCrBox!"}, status_code=200)


# Exception handlers ---------------------------------------------------------------------------------------------------
# https://docs.litestar.dev/2/usage/exceptions.html#configuration-exceptions


def handle_uncaught_exception(_request: Request, exception: Exception) -> QCrBoxResponse:
    """Handle uncaught exceptions."""
    status_code = getattr(exception, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exception, "detail", "There has been an unspecified error")
    return QCrBoxResponse(
        {
            "status": "error",
            "error": {
                "code": status_code,
                "message": detail,
            },
        },
        status_code=status_code,
    )


# Router aggregation ---------------------------------------------------------------------------------------------------


api_router = Router(
    path="/api",
    route_handlers=[
        # Datasets
        delete_dataset_by_id,
        list_datasets,
        get_dataset_by_id,
        create_dataset,
        download_dataset_by_id,
        # Data files
        list_data_files,
        get_data_file_by_id,
        create_data_file,
        download_data_file_by_id,
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
        create_interactive_session_with_data_file,
        close_interactive_session,
        # Health & Root
        healthz,
        index,
    ],
    exception_handlers={
        HTTPException: handle_uncaught_exception,
        # ValidationException: handle_uncaught_exception,
        # NotFoundException: handle_uncaught_exception,
        # InternalServerException: handle_uncaught_exception,
        # ServiceUnavailableException: handle_uncaught_exception,
    },
    response_class=QCrBoxResponse,
)
