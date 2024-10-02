from pathlib import Path
from typing import Annotated

import jinjax
from litestar import MediaType, Request, Response, Router, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

from pyqcrbox import msg_specs, sql_models

from ..api import api_helpers

__all__ = []

here = Path(__file__).parent

catalog = jinjax.Catalog(root_url="/views/static/components", file_ext=".jinjax")
catalog.add_folder(here / "components")


def render(*args, **kwargs) -> Response:
    rendered_content = catalog.render(*args, **kwargs)
    return Response(content=rendered_content, media_type=MediaType.HTML)


@get(path="/", media_type=MediaType.HTML)
async def views_root_handler() -> str:
    return "<html><h1>Hello world!</h1></html>"


@get(path="/applications")
async def serve_applications_page() -> Response:
    applications = api_helpers._retrieve_applications()
    commands = api_helpers._retrieve_commands()
    return render(
        "ApplicationsPage",
        applications=applications,
        commands=commands,
    )


@post(path="/invoke_command", media_type=MediaType.JSON)
async def display_invoke_command_button(data: sql_models.CommandInvocationCreate, request: Request) -> Response:
    # Get JSON data from the request
    response_json = await api_helpers._invoke_command(data)
    invoked_command_info = msg_specs.QCrBoxGenericResponse(**response_json)

    return render("InvokeCommandButton", invoked_command_info=invoked_command_info)


@get(path="/command/{cmd_id:int}", media_type=MediaType.HTML)
async def get_command_details(cmd_id: int) -> Response:
    command = api_helpers._retrieve_command_by_id(cmd_id, raise_if_not_found=False)
    return render("CommandDetails", command=command)


@get(path="/data_files")
async def serve_data_files_page() -> Response:
    return render("DataFilesPage", data_files=await api_helpers._get_data_files())


@post(path="/data_files/upload", media_type=MediaType.TEXT)
async def handle_data_file_upload(data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)]) -> str:
    _qcrbox_data_file_id = await api_helpers._import_data_file(data)
    return render("DataFilesList", data_files=await api_helpers._get_data_files())


views_router = Router(
    path="/views",
    route_handlers=[
        views_root_handler,
        serve_applications_page,
        serve_data_files_page,
        handle_data_file_upload,
        get_command_details,
        display_invoke_command_button,
    ],
)
