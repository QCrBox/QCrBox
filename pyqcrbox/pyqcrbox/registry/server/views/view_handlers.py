from pathlib import Path
from typing import Annotated

import jinjax
from litestar import MediaType, Response, Router, get, post
from litestar.datastructures import ResponseHeader, UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.status_codes import HTTP_200_OK, HTTP_206_PARTIAL_CONTENT

from pyqcrbox.data_management import DatasetNotFoundError
from pyqcrbox.debug import log_entry_exit
from pyqcrbox.helpers import as_bool
from pyqcrbox.logging import logger
from pyqcrbox.services import get_nats_broker
from pyqcrbox.sql_models import CommandInvocationCreate

from ..api import api_helpers

__all__ = []

here = Path(__file__).parent

catalog = jinjax.Catalog(root_url="/views/static/components", file_ext=".jinjax")
catalog.add_folder(here / "components")
catalog.jinja_env.filters["as_bool"] = as_bool


@log_entry_exit
def render(*args, _status_code=HTTP_200_OK, **kwargs) -> Response:
    rendered_content = catalog.render(*args, **kwargs)
    return Response(content=rendered_content, media_type=MediaType.HTML, status_code=_status_code)


@get(path="/index", media_type=MediaType.HTML)
@log_entry_exit
async def serve_qcrbox_homepage() -> Response:
    return render("QCrBoxHomePage")


@get(path="/applications")
@log_entry_exit
async def serve_applications_page() -> Response:
    applications = api_helpers.retrieve_applications()
    commands = api_helpers.retrieve_commands()
    return render(
        "ApplicationsPage",
        applications=applications,
        commands=commands,
    )


@get(path="/command/{cmd_id:int}", media_type=MediaType.HTML)
@log_entry_exit
async def get_command_details(cmd_id: int) -> Response:
    command = api_helpers.retrieve_command_by_id(cmd_id, raise_if_not_found=False)
    return render("CommandDetails", command=command)


@get(path="/data_files")
@log_entry_exit
async def serve_data_files_page() -> Response:
    return render("DataFilesPage", data_files=await api_helpers.get_data_files())


@post(path="/data_files/upload", media_type=MediaType.TEXT)
@log_entry_exit
async def handle_data_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    _qcrbox_data_file_id = await api_helpers.import_data_file(data)
    return render("DataFilesList", data_files=await api_helpers.get_data_files())


@post(path="/datasets/new", media_type=MediaType.TEXT)
@log_entry_exit
async def handle_dataset_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    dataset_id = await api_helpers.import_dataset(data)
    dataset_info = await api_helpers.get_dataset_info(dataset_id)
    applications = api_helpers.retrieve_applications()
    return render("DatasetUploadResponse", dataset_info=dataset_info, applications=applications)


@post(path="/interactive/start_session")
@log_entry_exit
async def start_interactive_session_with_data_file(
    application_name: str, application_slug: str, application_version: str, data_file_id: str
) -> Response:
    cmd = CommandInvocationCreate(
        application_slug=application_slug,
        application_version=application_version,
        command_name="interactive_session",
        arguments={"input_file": {"data_file_id": data_file_id}},
    )

    response_json = await api_helpers.invoke_command(cmd)
    interactive_session_id = response_json["payload"]["calculation_id"]
    return render(
        "StartInteractiveSessionResponse",
        application_name=application_name,
        interactive_session_id=interactive_session_id,
    )


@post(path="/interactive/close_session")
@log_entry_exit
async def close_interactive_session(session_id: str) -> Response:
    response_json = await api_helpers.close_interactive_session(session_id)
    try:
        output_dataset_info = await api_helpers.get_dataset_info(response_json.output_dataset_id)
    except DatasetNotFoundError:
        return render("StopInteractiveSessionResponseNoOutputDataset", _status_code=HTTP_206_PARTIAL_CONTENT)

    applications = api_helpers.retrieve_applications()
    return render(
        "StopInteractiveSessionResponse",
        dataset_info=output_dataset_info,
        applications=applications,
    )


@post(path="/start_olex2_session")
@log_entry_exit
async def start_olex2_interactive_session() -> Response:
    return render("StartOlexSessionResponse")


@get(path="/view_start_session_button")
@log_entry_exit
async def view_interactive_session_button(
    data_file_id: str, application_name: str, application_slug: str, application_version: str
) -> Response:
    return render(
        "StartInteractiveSessionButton",
        application_name=application_name,
        application_slug=application_slug,
        application_version=application_version,
        data_file_id=data_file_id,
    )


@get(path="/view_start_crystal_explorer_session_button")
@log_entry_exit
async def view_crystal_explorer_interactive_session_button() -> Response:
    return render("StartCrystalExplorerButton")


@post(path="/start_crystal_explorer_session")
@log_entry_exit
async def start_crystal_explorer_interactive_session() -> Response:
    return render("StartCrystalExplorerSessionResponse")


@post(path="/close_crystal_explorer_session")
@log_entry_exit
async def close_crystal_explorer_session() -> Response:
    return render("StopCrystalExplorerSessionResponse")


@get(path="/restart")
@log_entry_exit
async def serve_restart_docker_containers_page() -> Response:
    return render("RestartDockerContainersPage")


@post(
    path="/restart_docker_containers",
    media_type=MediaType.HTML,
    response_headers=[ResponseHeader(name="HX-Refresh", value="true")],
)
@log_entry_exit
async def restart_docker_containers() -> None:
    logger.debug("Sending NATS message to restart docker containers")

    nats_broker = await get_nats_broker()
    await nats_broker.publish("Please restart containers now", subject="restart-qcrbox-containers")
    logger.debug("NATS message sent, containers should be restarting shortly.")
    return render("RestartDockerContainersPage")


views_router = Router(
    path="/views",
    route_handlers=[
        serve_qcrbox_homepage,
        serve_applications_page,
        serve_data_files_page,
        handle_data_file_upload,
        handle_dataset_upload,
        get_command_details,
        start_interactive_session_with_data_file,
        close_interactive_session,
        view_interactive_session_button,
        view_crystal_explorer_interactive_session_button,
        start_crystal_explorer_interactive_session,
        close_crystal_explorer_session,
        serve_restart_docker_containers_page,
        restart_docker_containers,
    ],
)
