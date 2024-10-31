from pathlib import Path
from typing import Annotated

import jinjax
from litestar import MediaType, Response, Router, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from pyqcrbox.sql_models import CommandInvocationCreate

from ..api import api_helpers

__all__ = []

here = Path(__file__).parent

catalog = jinjax.Catalog(root_url="/views/static/components", file_ext=".jinjax")
catalog.add_folder(here / "components")


def render(*args, **kwargs) -> Response:
    rendered_content = catalog.render(*args, **kwargs)
    return Response(content=rendered_content, media_type=MediaType.HTML)


@get(path="/index", media_type=MediaType.HTML)
async def serve_qcrbox_homepage() -> Response:
    return render("QCrBoxHomePage")


@get(path="/applications")
async def serve_applications_page() -> Response:
    applications = api_helpers._retrieve_applications()
    commands = api_helpers._retrieve_commands()
    return render(
        "ApplicationsPage",
        applications=applications,
        commands=commands,
    )


@get(path="/command/{cmd_id:int}", media_type=MediaType.HTML)
async def get_command_details(cmd_id: int) -> Response:
    command = api_helpers._retrieve_command_by_id(cmd_id, raise_if_not_found=False)
    return render("CommandDetails", command=command)


@get(path="/data_files")
async def serve_data_files_page() -> Response:
    return render("DataFilesPage", data_files=await api_helpers._get_data_files())


@post(path="/data_files/upload", media_type=MediaType.TEXT)
async def handle_data_file_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    _qcrbox_data_file_id = await api_helpers._import_data_file(data)
    return render("DataFilesList", data_files=await api_helpers._get_data_files())


@post(path="/datasets/new", media_type=MediaType.TEXT)
async def handle_dataset_upload(
    data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> Response:
    dataset_id = await api_helpers._import_dataset(data)
    dataset_info = await api_helpers._get_dataset_info(dataset_id)
    applications = api_helpers._retrieve_applications()
    return render("DatasetUploadResponse", dataset_info=dataset_info, applications=applications)


@post(path="/interactive/start_session")
async def start_interactive_session_with_data_file(
    application_slug: str, application_version: str, data_file_id: str
) -> Response:
    cmd = CommandInvocationCreate(
        application_slug=application_slug,
        application_version=application_version,
        command_name="interactive_session",
        arguments={"input_file": {"data_file_id": data_file_id}},
    )

    await api_helpers._invoke_command(cmd)
    return render("StartSessionResponse")


@post(path="/start_session")
async def start_interactive_session() -> Response:
    return render("StartSessionResponse")


@get(path="/view_start_session_button")
async def view_interactive_session_button(
    data_file_id: str, application_slug: str, application_version: str
) -> Response:
    return render(
        "StartInteractiveSessionButton",
        application_slug=application_slug,
        application_version=application_version,
        data_file_id=data_file_id,
    )


@post(path="/close_session")
async def close_session() -> Response:
    datafile_name = "processed_file.cif"
    return render("StopSessionResponse", datafile_name=datafile_name)


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
        start_interactive_session,
        view_interactive_session_button,
        close_session,
    ],
)
