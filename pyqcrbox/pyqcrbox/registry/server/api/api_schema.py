from typing import Any, Generic, TypeVar

from litestar.openapi.datastructures import ResponseSpec
from pydantic import BaseModel

from pyqcrbox.data_management.data_file import DataFileMetadataResponse, DatasetResponse
from pyqcrbox.sql_models.application_spec import ApplicationSpecWithCommands
from pyqcrbox.sql_models.calculation import CalculationResponseModel
from pyqcrbox.sql_models.command_spec import CommandSpecWithParameters
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfoResponse

T = TypeVar("T")

# Requests


class InteractiveSessionCreate(BaseModel):
    application_slug: str
    application_version: str
    arguments: dict[str, Any]


# Success response


class QCrBoxResponse(BaseModel, Generic[T]):
    """Pydantic model for QCrBox API response specification."""

    status: str
    message: str
    timestamp: str
    payload: T


class ApplicationsResponse(BaseModel):
    applications: list[ApplicationSpecWithCommands]


class CalculationsResponse(BaseModel):
    calculations: list[CalculationResponseModel]


class CommandsResponse(BaseModel):
    commands: list[CommandSpecWithParameters]


class DataFilesResponse(BaseModel):
    data_files: list[DataFileMetadataResponse]


class DatasetsResponse(BaseModel):
    datasets: list[DatasetResponse]


class InteractiveSessionsResponse(BaseModel):
    interactive_sessions: list[InteractiveSessionInfoResponse]


class InteractiveSessionIDResponse(BaseModel):
    interactive_session_id: str


# Error response


class ErrorResponse(BaseModel):
    code: int
    message: str
    details: str | list[str]


class QCrBoxErrorResponse(BaseModel):
    """Pydantic model for QCrBox API error response specification."""

    status: str
    error: ErrorResponse


INTERNAL_SERVER_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Internal server error")
BAD_REQUEST_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Bad request syntax")
NOT_FOUND_ERROR = ResponseSpec(QCrBoxErrorResponse, generate_examples=False, description="Object not found")
