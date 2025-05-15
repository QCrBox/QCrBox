from typing import Generic, TypeVar

from pydantic import BaseModel

from pyqcrbox.data_management.data_file import DataFileMetadataResponse, DatasetResponse
from pyqcrbox.sql_models.application_spec import ApplicationSpecWithCommands
from pyqcrbox.sql_models.calculation import CalculationResponseModel

T = TypeVar("T")

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


class DataFilesResponse(BaseModel):
    data_files: list[DataFileMetadataResponse]


class DatasetsResponse(BaseModel):
    datasets: list[DatasetResponse]


# Error response


class ErrorResponse(BaseModel):
    code: int
    message: str


class QCrBoxErrorResponseSpec(BaseModel):
    """Pydantic model for QCrBox API error response specification."""

    status: str
    error: ErrorResponse
