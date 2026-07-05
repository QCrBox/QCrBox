# type: ignore

"""API endpoints for QCrBox, grouped by resource."""

import traceback
from typing import Annotated

import nats.errors
import nats.js.errors
from faststream.nats import NatsBroker
from litestar import MediaType, Request, Router, delete, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException, HTTPException
from litestar.params import Body, Parameter
from litestar.response import Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

from pyqcrbox import settings
from pyqcrbox.data_management import DataManager, DatasetNotFoundError
from pyqcrbox.registry.server.api import api_schema as schema
from pyqcrbox.registry.shared.qcrbox_response import QCrBoxResponse
from pyqcrbox.services.orchestrator import (
    ApplicationNotRegisteredError,
    ContainerOrchestrator,
    InstanceNotManagedError,
    OrchestratorDisabledError,
    OrchestratorError,
    SpawnNotPossibleError,
    SpawnQuotaExceededError,
    SpawnTimeoutError,
)
from pyqcrbox.sql_models import ApplicationSpec, CalculationStatusEnum, CommandInvocationCreate

from . import api_helpers

__all__ = ["api_router"]


class QCrBoxAPIException(HTTPException):
    pass


async def _ensure_live_container_exists_or_spawn(
    application_slug: str,
    application_version: str,
    orchestrator: ContainerOrchestrator,
    owner: str | None = None,
) -> str | None:
    """Ensure a live container exists for the application, spawning one on demand when possible.

    Fails fast with 404 (application unknown) or 503 (no live container and
    orchestration disabled); maps spawn failures to 503/504.

    With a known `owner` and orchestration enabled, the request is strictly
    bound to a container owned by that user (ensured/spawned as needed) and
    the bound instance's private inbox is returned for targeted dispatch.
    Anonymous requests use the shared pool (broadcast dispatch, return None).
    """
    if owner is not None and orchestrator.enabled:
        try:
            instance = await orchestrator.ensure_instance(application_slug, application_version, owner=owner)
        except SpawnTimeoutError as spawn_exc:
            raise QCrBoxAPIException(detail=str(spawn_exc), status_code=504) from spawn_exc
        except ApplicationNotRegisteredError as spawn_exc:
            raise QCrBoxAPIException(detail=str(spawn_exc), status_code=404) from spawn_exc
        except OrchestratorError as spawn_exc:
            raise QCrBoxAPIException(detail=str(spawn_exc), status_code=503) from spawn_exc
        return instance.private_inbox

    try:
        api_helpers.ensure_live_container_exists(application_slug, application_version)
    except api_helpers.ApplicationNotFoundError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=404) from exc
    except api_helpers.NoLiveContainerError as exc:
        if not orchestrator.enabled:
            raise QCrBoxAPIException(detail=str(exc), status_code=503) from exc
        try:
            await orchestrator.ensure_instance(application_slug, application_version, owner=owner)
        except SpawnTimeoutError as spawn_exc:
            raise QCrBoxAPIException(detail=str(spawn_exc), status_code=504) from spawn_exc
        except OrchestratorError as spawn_exc:
            raise QCrBoxAPIException(detail=str(spawn_exc), status_code=503) from spawn_exc
    return None


# Admin ----------------------------------------------------------------------------------------------------------------


@get(path="/healthz", media_type=MediaType.JSON, summary="Health check", tags=["admin"], operation_id="healthz")
async def healthz() -> schema.QCrBoxHealthResponse:
    """Check the health of the QCrBox registry."""
    return QCrBoxResponse(
        content={
            "status": "ok",
        },
        status_code=200,
    )


@get(path="/auth/gui", media_type=MediaType.JSON, include_in_schema=False)
async def authorize_gui_access(request: Request, current_user: str | None) -> Response:
    """Traefik forwardAuth endpoint authorizing access to per-instance GUI routes.

    Chained after the Authelia forwardAuth middleware on spawned GUI routers:
    Authelia authenticates the user (Remote-User), this endpoint authorizes the
    user against the instance's owner. The target instance is identified by the
    X-Forwarded-Host of the original request. Ownerless instances are open to
    any authenticated user; owned instances only to their owner.
    """
    from pyqcrbox.services.persistence import SQLitePersistenceAdapter

    forwarded_host = request.headers.get("x-forwarded-host")
    if not forwarded_host or current_user is None:
        return Response(content={"status": "denied"}, status_code=403)

    instance = await SQLitePersistenceAdapter().get_instance_by_gui_host(forwarded_host)
    if instance is None:
        return Response(content={"status": "denied", "reason": "unknown host"}, status_code=403)
    if instance.owner_user_id is not None and instance.owner_user_id != current_user:
        return Response(content={"status": "denied", "reason": "not the owner"}, status_code=403)

    return Response(content={"status": "ok"}, status_code=200)


@get(path="/", media_type=MediaType.JSON, include_in_schema=False)
async def index() -> Response:
    return Response(
        content={
            "status": "success",
            "message": "Hello from QCrBox!",
        },
        status_code=200,
    )


@get(path="/schema", media_type=MediaType.JSON, include_in_schema=False)
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


@post(
    path="/applications",
    media_type=MediaType.JSON,
    summary="Register an application",
    tags=["applications"],
    operation_id="register_application",
    responses={400: schema.BAD_REQUEST_ERROR, 409: schema.CONFLICT_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def register_application(
    data: Annotated[ApplicationSpec, Body()],
) -> schema.QCrBoxResponse[schema.ApplicationsResponse]:
    """Register an application spec without requiring a running container.

    Registration is idempotent: re-registering an existing application
    (same slug and version) updates its commands if they changed.
    """
    try:
        application = api_helpers.register_application_spec(data)
    except api_helpers.PyQCrBoxVersionMismatchError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=409) from exc

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Registered application {data.slug!r} (version {data.version!r})",
            "payload": {
                "applications": [application],
            },
        },
        status_code=201,
    )


# Container instances --------------------------------------------------------------------------------------------------


@get(
    path="/container-instances",
    media_type=MediaType.JSON,
    summary="List container instances",
    tags=["container-instances"],
    operation_id="list_container_instances",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def list_container_instances(
    slug: str | None = Parameter(default=None, query="slug", required=False),
    version: str | None = Parameter(default=None, query="version", required=False),
    owner: str | None = Parameter(default=None, query="owner", required=False),
) -> schema.QCrBoxResponse[schema.ContainerInstancesResponse]:
    """Retrieve the tracked container instances (live application containers)."""
    container_instances = api_helpers.retrieve_container_instances(
        application_slug=slug, application_version=version, owner=owner
    )
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Retrieved {len(container_instances)} container instances.",
            "payload": {
                "container_instances": container_instances,
            },
        },
        status_code=200,
    )


@post(
    path="/container-instances",
    media_type=MediaType.JSON,
    summary="Spawn a container instance",
    tags=["container-instances"],
    operation_id="create_container_instance",
    responses={
        404: schema.NOT_FOUND_ERROR,
        409: schema.CONFLICT_ERROR,
        503: schema.SERVICE_UNAVAILABLE_ERROR,
        504: schema.GATEWAY_TIMEOUT_ERROR,
    },
)
async def create_container_instance(
    data: Annotated[schema.CreateContainerInstanceParameters, Body()],
    orchestrator: ContainerOrchestrator,
    current_user: str | None,
) -> schema.QCrBoxResponse[schema.ContainerInstancesResponse]:
    """Spawn a new container for the given application (requires the orchestrator to be enabled)."""
    try:
        instance = await orchestrator.spawn_instance(
            data.application_slug, data.application_version, owner=current_user
        )
    except OrchestratorDisabledError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=503) from exc
    except SpawnQuotaExceededError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=409) from exc
    except ApplicationNotRegisteredError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=404) from exc
    except SpawnNotPossibleError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=409) from exc
    except SpawnTimeoutError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=504) from exc

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Spawned container instance for {data.application_slug!r} "
            f"(version {data.application_version!r})",
            "payload": {
                "container_instances": [
                    instance.to_response_model(
                        application_slug=data.application_slug, application_version=data.application_version
                    )
                ],
            },
        },
        status_code=201,
    )


@delete(
    path="/container-instances/{id:int}",
    media_type=MediaType.JSON,
    summary="Remove a container instance",
    tags=["container-instances"],
    operation_id="delete_container_instance",
    status_code=204,
    responses={
        404: schema.NOT_FOUND_ERROR,
        409: schema.CONFLICT_ERROR,
        503: schema.SERVICE_UNAVAILABLE_ERROR,
    },
)
async def delete_container_instance(id: int, orchestrator: ContainerOrchestrator) -> None:
    """Stop and remove an orchestrator-managed container instance."""
    try:
        removed = await orchestrator.remove_instance(id)
    except OrchestratorDisabledError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=503) from exc
    except InstanceNotManagedError as exc:
        raise QCrBoxAPIException(detail=str(exc), status_code=409) from exc
    if not removed:
        raise QCrBoxAPIException(detail=f"Container instance not found: {id}", status_code=404)


# Calculations ---------------------------------------------------------------------------------------------------------


@get(
    path="/calculations",
    media_type=MediaType.JSON,
    summary="List all calculations",
    tags=["calculations"],
    operation_id="list_calculations",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def list_calculations(data_manager: DataManager) -> schema.QCrBoxResponse[schema.CalculationsResponse]:
    """Retrieve a list of all calculations, past and present."""
    calculations = await api_helpers.get_calculations(data_manager=data_manager)

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
async def get_calculation_by_id(
    id: str = Parameter(title="Calculation ID"), *, data_manager: DataManager
) -> schema.QCrBoxResponse[schema.CalculationsResponse]:
    """Retrieve a calculation by its ID."""
    try:
        calculation = await api_helpers.get_calculation_by_calculation_id(id, data_manager=data_manager)
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


@post(
    path="/calculations/{id:str}/stop",
    media_type=MediaType.JSON,
    summary="Stop a running calculation",
    tags=["calculations"],
    operation_id="stop_running_calculation",
    status_code=200,
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def stop_running_calculation(
    id: str = Parameter(title="Calculation ID"), *, nats_broker: NatsBroker, data_manager: DataManager
) -> schema.QCrBoxResponse[schema.CalculationStoppedResponse]:
    """Stop a currently running command, interactive and non-interactive."""
    try:
        stopped_calculation = await api_helpers.stop_running_calculation(
            id, data_manager=data_manager, nats_broker=nats_broker
        )
    except KeyError as exc:
        raise QCrBoxAPIException(detail=f"No calculation with ID {id!r}", status_code=404) from exc
    except (nats.errors.NoRespondersError, nats.errors.NoServersError) as exc:
        raise QCrBoxAPIException(
            detail=f"Unable to contact application to request to stop calculation {id!r}", status_code=404
        ) from exc
    except TypeError as exc:
        raise QCrBoxAPIException(
            detail="There was an internal server error when processing your request", status_code=500
        ) from exc

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Stopped calculation {stopped_calculation.calculation_id}",
            "payload": {
                "calculations": [
                    stopped_calculation,
                ]
            },
        },
        status_code=200,
    )


# Commands -------------------------------------------------------------------------------------------------------------


@get(
    path="/commands",
    media_type=MediaType.JSON,
    summary="List all commands",
    tags=["commands"],
    operation_id="list_commands",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
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


@post(
    path="/commands",
    media_type=MediaType.JSON,
    summary="Invoke a command with arguments",
    tags=["commands"],
    operation_id="invoke_command",
    responses={
        400: schema.BAD_REQUEST_ERROR,
        404: schema.NOT_FOUND_ERROR,
        500: schema.INTERNAL_SERVER_ERROR,
        503: schema.SERVICE_UNAVAILABLE_ERROR,
    },
)
async def invoke_command(
    data: Annotated[schema.InvokeCommandParameters, Body()],
    nats_broker: NatsBroker,
    orchestrator: ContainerOrchestrator,
    current_user: str | None,
) -> schema.QCrBoxResponse[schema.InvokeCommandResponse]:
    """Create an interactive session with the provided arguments."""
    target_private_inbox = await _ensure_live_container_exists_or_spawn(
        data.application_slug, data.application_version, orchestrator, owner=current_user
    )
    command_spec = CommandInvocationCreate(
        application_slug=data.application_slug,
        application_version=data.application_version,
        command_name=data.command_name,
        arguments=data.command_arguments,
    )
    try:
        response = await api_helpers.invoke_command(
            command_spec, nats_broker=nats_broker, target_private_inbox=target_private_inbox
        )
    except (nats.errors.NoRespondersError, nats.errors.NoServersError) as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command, unable to find {data.application_slug}-{data.application_version} container inbox",
            status_code=404,
        ) from exc
    except ClientException as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command due to incorrect request: {data}",
            status_code=400,
        ) from exc
    except Exception as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command due to an error in the server {str(exc)}", status_code=400
        ) from exc

    if response["status"] != CalculationStatusEnum.SUBMITTED:
        error_msg = response["payload"].get("error", "an unknown error occurred")
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command: {error_msg}",
            status_code=500,
        )

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Command invocation accepted: {data.application_slug!r}-{data.application_version!r}",
            "payload": {
                "calculation_id": response["payload"]["calculation_id"],
            },
        },
        status_code=201,
    )


# Data files -----------------------------------------------------------------------------------------------------------


@get(
    path="/data-files",
    media_type=MediaType.JSON,
    summary="List all data files",
    tags=["data-files"],
    operation_id="list_data_files",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def list_data_files(data_manager: DataManager) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Retrieve a list of all data files in the data store."""
    data_files = await api_helpers.get_data_files(data_manager=data_manager)
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
async def get_data_file_by_id(
    id: str = Parameter(title="Data file ID"), *, data_manager: DataManager
) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Retrieve a data files by it's ID."""
    try:
        data_file = await api_helpers.get_data_file_info(id, data_manager=data_manager)
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


@get(
    path="/data-files/{id:str}/download",
    media_type="application/octet-stream",
    summary="Download a data file",
    tags=["data-files"],
    operation_id="download_data_file_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def download_data_file_by_id(
    id: str = Parameter(title="Data file ID"), *, data_manager: DataManager
) -> Response[bytes]:
    """Download a data file from the data store."""
    try:
        data_file_contents_as_bytes, data_file_name = await api_helpers.export_data_file(id, data_manager=data_manager)
    except nats.js.errors.NotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Data file not found: {id!r}", status_code=404) from exc

    return Response(
        content=data_file_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={data_file_name!r}"},
    )


@delete(
    path="/data-files/{id:str}",
    summary="Delete a data file",
    tags=["data-files"],
    operation_id="delete_data_file_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def delete_data_file_by_id(id: str = Parameter(title="Data file ID"), *, data_manager: DataManager) -> None:
    """Remove a dataset and associated data files from the data store."""
    await api_helpers.delete_data_file(id, data_manager=data_manager)


@post(
    path="/data-files",
    media_type=MediaType.JSON,
    summary="Create a new data file",
    tags=["data-files"],
    operation_id="create_data_file",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def create_data_file(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)], data_manager: DataManager
) -> schema.QCrBoxResponse[schema.DataFilesResponse]:
    """Create a new dataset by uploading data files."""
    qcrbox_data_file_id = await api_helpers.import_data_file(data, data_manager=data_manager)
    data_file = await api_helpers.get_data_file_info(qcrbox_data_file_id, data_manager=data_manager)

    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Created data file: {qcrbox_data_file_id!r}",
            "payload": {
                "data_files": [data_file],
            },
        },
        status_code=201,
    )


# Datasets -------------------------------------------------------------------------------------------------------------


@delete(
    path="/datasets/{id:str}",
    summary="Delete a dataset",
    tags=["datasets"],
    operation_id="delete_dataset_by_id",
    responses={400: schema.BAD_REQUEST_ERROR, 404: schema.NOT_FOUND_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def delete_dataset_by_id(id: str = Parameter(title="Dataset ID"), *, data_manager: DataManager) -> None:
    """Remove a dataset and associated data files from the data store."""
    await api_helpers.delete_dataset(id, data_manager=data_manager)


@get(
    path="/datasets",
    media_type=MediaType.JSON,
    summary="List all datasets",
    tags=["datasets"],
    operation_id="list_datasets",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def list_datasets(data_manager: DataManager) -> schema.QCrBoxResponse[schema.DatasetsResponse]:
    """Retrieve a list of all datasets in the data store."""
    datasets = await api_helpers.get_datasets(data_manager=data_manager)
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
async def get_dataset_by_id(
    id: str = Parameter(title="Dataset ID"), *, data_manager: DataManager
) -> schema.QCrBoxResponse[schema.DatasetsWithDataFilesResponse]:
    """Retrieve a dataset by its ID, including metadata of linked data files."""
    try:
        dataset = await api_helpers.get_dataset_info(id, data_manager=data_manager)
        return QCrBoxResponse(
            content={
                "status": "success",
                "message": f"Retrieved dataset: {id!r}",
                "payload": {
                    "datasets": [dataset],
                    "data_files": list(dataset.data_files.values()),
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
async def create_dataset(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)], data_manager: DataManager
) -> schema.QCrBoxResponse[schema.DatasetsWithDataFilesResponse]:
    """Create a new dataset by uploading data files."""
    qcrbox_dataset_id = await api_helpers.import_dataset(data, data_manager=data_manager)
    dataset = await api_helpers.get_dataset_info(qcrbox_dataset_id, data_manager=data_manager)
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Created dataset: {qcrbox_dataset_id!r}",
            "payload": {
                "datasets": [dataset],
                "data_files": list(dataset.data_files.values()),
            },
        },
        status_code=201,
    )


@post(
    path="/datasets/{id:str}/append",
    media_type=MediaType.JSON,
    summary="Add a file to a dataset",
    tags=["datasets"],
    operation_id="append_to_dataset",
    responses={400: schema.BAD_REQUEST_ERROR, 500: schema.INTERNAL_SERVER_ERROR},
)
async def append_to_dataset(
    id: str,
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
    *,
    data_manager: DataManager,
) -> schema.QCrBoxResponse[schema.DatasetAppendResponse]:
    """Append a new data file to a dataset."""
    dataset_id = await api_helpers.append_to_dataset(id, data, data_manager=data_manager)
    dataset = await api_helpers.get_dataset_info(dataset_id, data_manager=data_manager)
    appended_file = dataset.data_files[data.filename]
    return QCrBoxResponse(
        content={
            "status": "success",
            "message": f"Appended data file {appended_file.qcrbox_file_id!r} to dataset {dataset_id!r}",
            "payload": {
                "datasets": [dataset],
                "data_files": list(dataset.data_files.values()),
                "appended_file": appended_file,
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
async def download_dataset_by_id(
    id: str = Parameter(title="Dataset ID"), *, data_manager: DataManager
) -> Response[bytes]:
    """Download the data files of a datast as a Zip file."""
    try:
        dataset_contents_as_bytes, output_filename = await api_helpers.export_dataset(id, data_manager=data_manager)
    except DatasetNotFoundError as exc:
        raise QCrBoxAPIException(detail=f"Dataset not found: {id!r}", status_code=404) from exc

    return Response(
        content=dataset_contents_as_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={output_filename}"},
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
async def list_interactive_sessions(
    data_manager: DataManager,
) -> schema.QCrBoxResponse[schema.InteractiveSessionsResponse]:
    """Retrieve a list of interactive sessions, past and present."""
    interactive_sessions = await api_helpers.get_interactive_sessions(data_manager=data_manager)
    interactive_sessions = api_helpers.with_gui_urls(interactive_sessions)
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
async def get_interactive_session_by_id(
    id: str = Parameter(title="Interactive session ID"), *, data_manager: DataManager
) -> schema.QCrBoxResponse[schema.InteractiveSessionsResponse]:
    """Retrieve and interactive session of the given ID."""
    try:
        interactive_session = await api_helpers.get_interactive_session_info(id, data_manager=data_manager)
        (interactive_session,) = api_helpers.with_gui_urls([interactive_session])
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
    operation_id="create_interactive_session",
    responses={
        400: schema.BAD_REQUEST_ERROR,
        404: schema.NOT_FOUND_ERROR,
        500: schema.INTERNAL_SERVER_ERROR,
        503: schema.SERVICE_UNAVAILABLE_ERROR,
        504: schema.GATEWAY_TIMEOUT_ERROR,
    },
)
async def create_interactive_session_with_arguments(
    data: Annotated[schema.CreateInteractiveSessionParameters, Body()],
    nats_broker: NatsBroker,
    orchestrator: ContainerOrchestrator,
    current_user: str | None,
) -> schema.QCrBoxResponse[schema.InteractiveSessionIDResponse]:
    """Create an interactive session with the provided arguments arguments."""
    target_private_inbox = await _ensure_live_container_exists_or_spawn(
        data.application_slug, data.application_version, orchestrator, owner=current_user
    )
    command_spec = CommandInvocationCreate(
        application_slug=data.application_slug,
        application_version=data.application_version,
        command_name="interactive_session",
        arguments=data.command_arguments,
    )
    try:
        response = await api_helpers.invoke_command(
            command_spec, nats_broker=nats_broker, target_private_inbox=target_private_inbox
        )
    except (nats.errors.NoRespondersError, nats.errors.NoServersError) as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command, unable to find {data.application_slug}-{data.application_version} container inbox",
            status_code=404,
        ) from exc
    except ClientException as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command due to incorrect request: {data}",
            status_code=400,
        ) from exc
    except Exception as exc:
        raise QCrBoxAPIException(
            detail=f"Failed to invoke command due to exception {str(exc)}", status_code=500
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
async def close_interactive_session(
    id: str = Parameter(title="Interactive session ID"), *, data_manager: DataManager, nats_broker: NatsBroker
) -> schema.QCrBoxResponse[schema.InteractiveSessionClosedResponse]:
    """Close, potentially prematurely, an interactive session."""
    try:
        closed_session = await api_helpers.close_interactive_session(
            id, data_manager=data_manager, nats_broker=nats_broker
        )
    except KeyError as exc:
        raise QCrBoxAPIException(detail=f"Interactive session not found: {id!r}", status_code=404) from exc
    except (nats.errors.NoRespondersError, nats.errors.NoServersError) as exc:
        raise QCrBoxAPIException(
            detail=f"Unable to contact application to request to close session {id!r}", status_code=404
        ) from exc
    except TypeError as exc:
        raise QCrBoxAPIException(
            detail="There was an internal server error when processing your request", status_code=500
        ) from exc

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
        authorize_gui_access,
        # Applications
        list_applications,
        register_application,
        # Container instances
        list_container_instances,
        create_container_instance,
        delete_container_instance,
        # Calculations
        list_calculations,
        get_calculation_by_id,
        stop_running_calculation,
        # Commands
        list_commands,
        get_command_by_id,
        invoke_command,
        # Datasets
        delete_dataset_by_id,
        list_datasets,
        get_dataset_by_id,
        create_dataset,
        download_dataset_by_id,
        append_to_dataset,
        # Data files
        list_data_files,
        get_data_file_by_id,
        download_data_file_by_id,
        delete_data_file_by_id,
        create_data_file,
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
