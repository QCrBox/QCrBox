from pathlib import Path

import jinjax
from litestar import MediaType, Response, get

from pyqcrbox.data_management.data_file import QCrBoxDataFile

__all__ = []

here = Path(__file__).parent

catalog = jinjax.Catalog()
catalog.add_folder(here / "components")


def render(*args, **kwargs) -> Response:
    rendered_content = catalog.render(*args, **kwargs)
    return Response(content=rendered_content, media_type=MediaType.HTML)


@get(path="/data_files_page")
async def data_files_page() -> Response:
    # return render("DataFilesPage", data_files=await _get_data_files())
    return render(
        "DataFilesPage",
        data_files=[
            QCrBoxDataFile(qcrbox_file_id="123", filename="test1.txt", contents=b"Hello, world!"),
            QCrBoxDataFile(qcrbox_file_id="456", filename="test2.txt", contents=b""),
        ],
    )
