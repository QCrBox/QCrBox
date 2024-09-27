from pathlib import Path

import jinjax
from litestar import MediaType, Request, Response, Router, get, post

from pyqcrbox.data_management.data_file import QCrBoxDataFile

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


@post(path="/invoke_command")
async def display_invoke_command_button(request: Request) -> Response:
    # Get JSON data from the request
    data = await request.json()
    print(data)
    invoked_command_info = api_helpers._invoke_command(data)

    return render(
        "InvokeCommandButton",
        invoked_command_info=invoked_command_info,
    )


@get(path="/command/{cmd_id:int}", media_type=MediaType.HTML)
async def get_command_details(cmd_id: int) -> Response:
    command = api_helpers._retrieve_command_by_id(cmd_id, raise_if_not_found=False)
    return render("CommandDetails", command=command)


@get(path="/data_files")
async def serve_data_files_page() -> Response:
    # return render("DataFilesPage", data_files=await _get_data_files())
    return render(
        "DataFilesPage",
        data_files=[
            QCrBoxDataFile(qcrbox_file_id="123", filename="test1.txt", contents=b"Hello, world!"),
            QCrBoxDataFile(qcrbox_file_id="456", filename="test2.txt", contents=b""),
        ],
    )


views_router = Router(
    path="/views",
    route_handlers=[
        views_root_handler,
        serve_applications_page,
        serve_data_files_page,
        get_command_details,
        display_invoke_command_button,
    ],
)
