from pathlib import Path

import jinjax
from litestar import MediaType, Response, Router, get

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
    return render(
        "ApplicationsPage",
        applications=applications,
    )


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
    ],
)
