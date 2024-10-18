from pathlib import Path
from typing import Annotated

import jinjax
from litestar import MediaType, Response, Router, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body

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


@get(path="/workflow/{workflow_id:int}", media_type=MediaType.HTML)
async def serve_workflow_page(workflow_id: int) -> Response:
    workflow_items = []
    return render(
        "WorkflowPage",
        workflow_id=workflow_id,
        items=workflow_items,
    )


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


views_router = Router(
    path="/views",
    route_handlers=[
        serve_qcrbox_homepage,
        serve_applications_page,
        serve_data_files_page,
        serve_workflow_page,
        handle_data_file_upload,
        get_command_details,
    ],
)
