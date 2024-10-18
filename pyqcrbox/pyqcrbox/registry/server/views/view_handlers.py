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


class WorkflowStep:
    def __init__(self, *, workflow_id: int, step_id: int):
        self.step_id = step_id
        self.workflow_id = workflow_id
        self.is_empty = True

    @property
    def html_div_id(self):
        return f"workflow-{self.workflow_id}-step-{self.step_id}"


class Workflow:
    def __init__(self, *, title: str, steps: list[WorkflowStep], workflow_id: int):
        self.workflow_id = workflow_id
        self.title = title
        self.steps = steps


@get(path="/index", media_type=MediaType.HTML)
async def serve_qcrbox_homepage() -> Response:
    workflow_id = 1
    workflow_steps = [
        # WorkflowStep(workflow_id=workflow_id, step_id=1),
        # WorkflowStep(workflow_id=workflow_id, step_id=2),
    ]
    dummy_workflow = Workflow(title="Dummy Workflow", steps=workflow_steps, workflow_id=workflow_id)
    return render("QCrBoxHomePage", workflow=dummy_workflow)


@get(path="/workflows/{workflow_id:int}", media_type=MediaType.HTML)
async def serve_workflow_page(workflow_id: int) -> Response:
    workflow_steps = []
    return render(
        "WorkflowPage",
        workflow_id=workflow_id,
        steps=workflow_steps,
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


@post(path="/workflows/{workflow_id:int}/initial_dataset")
async def set_workflow_initial_dataset(workflow_id: int, qcrbox_data_file_id: str) -> Response:
    from pyqcrbox import logger

    logger.error(f"TODO: set initial dataset for workflow {workflow_id}")
    workflow_step = WorkflowStep(workflow_id=workflow_id, step_id=1)
    return render("WorkflowStep", step=workflow_step)


# @post(path="/workflows/<workflow_id:int>/steps/<workflow_step_id:int>")
# async def handle_workflow_step_update(workflow_id: int, workflow_step_id: int, qcrbox_data_file_id: str) -> Response:
#     return render("WorkflowStep", item=None)


views_router = Router(
    path="/views",
    route_handlers=[
        serve_qcrbox_homepage,
        serve_applications_page,
        serve_data_files_page,
        serve_workflow_page,
        handle_data_file_upload,
        set_workflow_initial_dataset,
        get_command_details,
    ],
)
