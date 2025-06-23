"""API endpoints for QCrBox, grouped by resource."""

import traceback
from typing import Annotated

import nats.js.errors
from litestar import MediaType, Request, Router, delete, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body, Parameter
from litestar.response import Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

from pyqcrbox import settings
from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import eel_logging
from pyqcrbox.registry.server.api import api_schema as schema
from pyqcrbox.registry.shared.qcrbox_response import QCrBoxResponse
from pyqcrbox.sql_models import CalculationStatusEnum, CommandInvocationCreate

from . import api_helpers

__all__ = ["api_router"]


class QCrBoxAPIException(HTTPException):
    pass


# Admin ----------------------------------------------------------------------------------------------------------------


@get(path="/healthz", media_type=MediaType.JSON, summary="Health check", tags=["admin"], operation_id="healthz")
@eel_logging
async def healthz() -> schema.QCrBoxHealthResponse:
    """Check the health of the QCrBox registry."""
    return QCrBoxResponse(
        content={
            "status": "ok",
        },
        status_code=200,
    )


@get(path="/", media_type=MediaType.JSON, include_in_schema=False)
@eel_logging
async def index() -> Response:
    return Response(
        content={
            "status": "success",
            "message": "Hello from QCrBox!",
        },
        status_code=200,
    )


@get(path="/openapi-schema", media_type=MediaType.JSON, include_in_schema=False)
async def openapi_schema(request: Request) -> dict:
    return request.app.openapi_schema.to_schema()


# Applications ---------------------------------------------------------------------------------------------------------


@get(
    path="/applications",
    media_type=MediaType.JSON,
    summary="List all applications",
    tags=["applications"],
    operation_id="list_applications",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def list_applications() -> schema.QCrBoxResponse[schema.ApplicationsResponse]:
    """Retrieve a list of registered applications."""
    applications = api_helpers.retrieve_applications()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Retrieved {len(applications)} applications.",
            "payload": {
                "applications": applications,
            },
        },
        status_code=200,
    )


# Calculations ---------------------------------------------------------------------------------------------------------


@get(
    path="/calculations",
    media_type=MediaType.JSON,
    summary="List all calculations",
    tags=["calculations"],
    operation_id="list_calculations",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def list_calculations() -> schema.QCrBoxResponse[schema.CalculationsResponse]:
    """Retrieve a list of all calculations, past and present."""
    calculations = await api_helpers.get_calculations()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Retrieved {len(calculations)} calculations",
            "payload": {
                "calculations": calculations,
            },
        },
        status_code=200,
    )


@get(
    path="/calculations/{id:str}",
    media_type=MediaType.JSON,
    summary="Get calculation by ID",
    tags=["calculations"],
    operation_id="get_calculation_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def get_calculation_by_id(
    id: str = Parameter(title="Calculation ID"),
) -> schema.QCrBoxResponse[schema.CalculationsResponse]:
    """Retrieve a calculation by its ID."""
    try:
        calculation = await api_helpers.get_calculation_by_calculation_id(id)
        return QCrBoxResponse(
            content={
                "status": "success",
                "message": f"Retrieved calculation: {id!r}",
                "payload": {
                    "calculations": [calculation],
                },
            },
            status_code=200,
        )
    except api_helpers.CalculationNotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Calculation not found: {id!r}", status_code=404) from exc


# Commands -------------------------------------------------------------------------------------------------------------


@get(
    path="/commands",
    media_type=MediaType.JSON,
    summary="List all commands",
    tags=["commands"],
    operation_id="list_commands",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def list_commands() -> schema.QCrBoxResponse[schema.CommandsResponse]:
    """Retrieve a list of commands, which are registered to applications."""
    commands = api_helpers.retrieve_commands()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": "Retrieved commands",
            "payload": {
                "commands": commands,
            },
        },
        status_code=200,
    )


@get(
    path="/commands/{id:int}",
    media_type=MediaType.JSON,
    summary="Get command by ID",
    tags=["commands"],
    operation_id="get_command_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def get_command_by_id(id: int) -> schema.QCrBoxResponse[schema.CommandsResponse]:
    """Retrieve a command of the given ID."""
    try:
        command = api_helpers.retrieve_command_by_id(id)
        return QCrBoxResponse(
            content={
                "status": "success",
                "message": f"Retrieved command: {id!r}",
                "payload": {
                    "commands": [command],
                },
            },
            status_code=200,
        )
    except api_helpers.CommandNotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Command not found: {id!r}", status_code=404) from exc


# Data files -----------------------------------------------------------------------------------------------------------


@get(
    path="/data-files",
    media_type=MediaType.JSON,
    summary="List all data files",
    tags=["data-files"],
    operation_id="list_data_files",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
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


@get(
    path="/data-files/{id:str}",
    media_type=MediaType.JSON,
    summary="Get a data file",
    tags=["data-files"],
    operation_id="get_data_file_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
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
    except KeyError as exc:
        raise QCrBoxAPIException(detail=f"Data file not found: {id!r}", status_code=404) from exc


# ----------------------------------------------------------------------------------------------------------------------
# Removed for now, as there SHOULD NOT be any mechanism to upload a data file which is not associated to a dataset.
# ----------------------------------------------------------------------------------------------------------------------
# @post(
#     path="/data-files",
#     media_type=MediaType.JSON,
#     summary="Upload a data file",
#     tags=["data-files"],
#     operation_id="create_data_file",
#     responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
# )
# @eel_logging
# async def create_data_file(
#     data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART, title="The file to upload")],
# ) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
#     """Upload a new data file to the data store."""
#     qcrbox_data_file_id = await api_helpers.import_data_file(data)
#     data_file = await api_helpers.get_data_file_info(qcrbox_data_file_id)
#     return QCrBoxResponse(
#         content={
#             "status": "success",
#             "message": f"Imported data file: {data.filename!r}",
#             "payload": {
#                 "data_files": [data_file],
#             },
#         },
#         status_code=201,
#     )
# ----------------------------------------------------------------------------------------------------------------------


@get(
    path="/data-files/{id:str}/download",
    media_type="application/octet-stream",
    summary="Download a data file",
    tags=["data-files"],
    operation_id="download_data_file_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def download_data_file_by_id(id: str = Parameter(title="Data file ID")) -> Response[bytes]:
    """Download a data file from the data store."""
    try:
        data_file_contents_as_bytes, data_file_name = await api_helpers.export_data_file(id)
    except nats.js.errors.NotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Data file not found: {id!r}", status_code=404) from exc

    return Response(
        content=data_file_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={data_file_name!r}"},
    )


# Datasets -------------------------------------------------------------------------------------------------------------


@delete(
    path="/datasets/{id:str}",
    summary="Delete a dataset",
    tags=["datasets"],
    operation_id="delete_dataset_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def delete_dataset_by_id(id: str = Parameter(title="Dataset ID")) -> None:
    """Remove a dataset and associated data files from the data store."""
    await api_helpers.delete_dataset(id)


@get(
    path="/datasets",
    media_type=MediaType.JSON,
    summary="List all datasets",
    tags=["datasets"],
    operation_id="list_datasets",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def list_datasets() -> schema.QCrBoxResponse[schema.DatasetsResponse]:
    """Retrieve a list of all datasets in the data store."""
    datasets = await api_helpers.get_datasets()
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Retrieved {len(datasets)} datasets",
            "payload": {
                "datasets": datasets,
            },
        },
        status_code=200,
    )


@get(
    path="/datasets/{id:str}",
    media_type=MediaType.JSON,
    summary="Get dataset by ID",
    tags=["datasets"],
    operation_id="get_dataset_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def get_dataset_by_id(
    id: str = Parameter(title="Dataset ID"),
) -> schema.QCrBoxResponse[schema.DatasetsResponse]:
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
    except (KeyError, DatasetNotFoundError) as exc:
        raise QCrBoxAPIException(detail=f"Dataset not found: {id!r}", status_code=404) from exc


@post(
    path="/datasets",
    media_type=MediaType.JSON,
    summary="Create a new dataset",
    tags=["datasets"],
    operation_id="create_dataset",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def create_dataset(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
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


@get(
    path="/datasets/{id:str}/download",
    media_type="application/octet-stream",
    summary="Download a dataset",
    tags=["datasets"],
    operation_id="download_dataset_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def download_dataset_by_id(id: str = Parameter(title="Dataset ID")) -> Response[bytes]:
    """Download the data files of a datast as a Zip file."""
    try:
        dataset_contents_as_bytes, output_filename = await api_helpers.export_dataset(id)
    except DatasetNotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Dataset not found: {id!r}", status_code=404) from exc

    return Response(
        content=dataset_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={output_filename!r}"},
        status_code=200,
    )


# Interactive sessions -------------------------------------------------------------------------------------------------


@get(
    path="/interactive-sessions",
    media_type=MediaType.JSON,
    summary="List all interactive sessions",
    tags=["interactive-sessions"],
    operation_id="list_interactive_sessions",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def list_interactive_sessions() -> schema.QCrBoxResponse[schema.InteractiveSessionsResponse]:
    """Retrieve a list of interactive sessions, past and present."""
    interactive_sessions = await api_helpers.get_interactive_sessions()
    return QCrBoxResponse(
        {
            "status": "success",
            "message": f"Retrieved {len(interactive_sessions)} interactive sessions",
            "payload": {
                "interactive_sessions": interactive_sessions,
            },
        },
        status_code=200,
    )


@get(
    path="/interactive-sessions/{id:str}",
    media_type=MediaType.JSON,
    summary="Get interactive session by ID",
    tags=["interactive-sessions"],
    operation_id="get_interactive_session_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def get_interactive_session_by_id(
    id: str = Parameter(title="Interactive session ID"),
) -> schema.QCrBoxResponse[schema.InteractiveSessionsResponse]:
    """Retrieve and interactive session of the given ID."""
    try:
        interactive_session = await api_helpers.get_interactive_session_info(id)
        return QCrBoxResponse(
            {
                "status": "success",
                "message": f"Retrieved interactive session: {id!r}",
                "payload": {
                    "interactive_sessions": [interactive_session],
                },
            },
            status_code=200,
        )
    except KeyError as exc:
        raise QCrBoxAPIException(detail=f"Interactive session not found: {id!r}", status_code=404) from exc


@post(
    path="/interactive-sessions",
    media_type=MediaType.JSON,
    summary="Create interactive session",
    tags=["interactive-sessions"],
    operation_id="create_interactive_session_with_arguments",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def create_interactive_session_with_arguments(
    data: Annotated[schema.CreateInteractiveSession, Body()],
) -> schema.QCrBoxResponse[schema.InteractiveSessionIDResponse]:
    """Create an interactive session with the provided arguments arguments."""
    command_spec = CommandInvocationCreate(
        application_slug=data.application_slug,
        application_version=data.application_version,
        command_name="interactive_session",
        arguments=data.arguments,
    )
    try:
        response = await api_helpers.invoke_command(command_spec)
    except Exception as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command due to exception {str(exc)}", status_code=400
        ) from exc

    if response["status"] != CalculationStatusEnum.SUBMITTED:
        error_msg = response["payload"].get("error", "an unknown error occurred")
        raise QCrBoxAPIException(
            detail=f"Failed to create interactive session: {error_msg}",
            status_code=500,
        )

    # TODO: we should respond with the created object, rather than the ID. But we can't do that just yet.
    # interactive_session = api_helpers.get_calculation_info_by_calculation_id(response["payload"]["calculation_id"])

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Command invocation accepted: {data.application_slug!r}-{data.application_version!r}",
            "payload": {
                "interactive_session_id": response["payload"]["calculation_id"],
            },
        },
        status_code=201,
    )


@post(
    path="/interactive-sessions/{id:str}/close",
    media_type=MediaType.JSON,
    summary="Close interactive session",
    tags=["interactive-sessions"],
    operation_id="close_interactive_session",
    status_code=200,
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
@eel_logging
async def close_interactive_session(
    id: str = Parameter(title="Interactive session ID"),
) -> schema.QCrBoxResponse[schema.InteractiveSessionClosedResponse]:
    """Close, potentially prematurely, an interactive session."""
    try:
        closed_session = await api_helpers.close_interactive_session(id)
    except KeyError as exc:
        raise QCrBoxAPIException(detail=f"Interactive session not found: {id!r}", status_code=404) from exc

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Closed interactive session: {id!r}",
            "payload": {
                "interactive_sessions": [
                    closed_session,
                ]
            },
        },
        status_code=200,
    )


# Exception handlers ---------------------------------------------------------------------------------------------------
# https://docs.litestar.dev/2/usage/exceptions.html#configuration-exceptions


def handle_exception(_request: Request, exception: Exception) -> schema.QCrBoxErrorResponse:
    """Handle uncaught exceptions."""
    status_code = getattr(exception, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    message = getattr(exception, "detail", "There has been an unspecified error")
    if settings.debug_mode:
        details = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    else:
        details = getattr(exception, "extra", None)

    return QCrBoxResponse(
        content={
            "status": "error",
            "error": {
                "code": status_code,
                "message": message,
                "details": details,
            },
        },
        status_code=status_code,
    )


# Router aggregation ---------------------------------------------------------------------------------------------------


api_router = Router(
    path="/api",
    route_handlers=[
        # admin
        healthz,
        index,
        openapi_schema,
        # Applications
        list_applications,
        # Calculations
        list_calculations,
        get_calculation_by_id,
        # Commands
        list_commands,
        get_command_by_id,
        # Datasets
        delete_dataset_by_id,
        list_datasets,
        get_dataset_by_id,
        create_dataset,
        download_dataset_by_id,
        # Data files
        list_data_files,
        get_data_file_by_id,
        # create_data_file,
        download_data_file_by_id,
        # Interactive sessions
        list_interactive_sessions,
        get_interactive_session_by_id,
        create_interactive_session_with_arguments,
        close_interactive_session,
    ],
    exception_handlers={
        HTTPException: handle_exception,
        Exception: handle_exception,
    },
    response_class=QCrBoxResponse,
)
