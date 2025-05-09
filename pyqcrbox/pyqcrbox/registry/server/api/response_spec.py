from typing import Generic, TypeVar

from pydantic import BaseModel

from pyqcrbox.data_management.data_file import DatasetResponse
from pyqcrbox.sql_models.application_spec import ApplicationSpecWithCommands
from pyqcrbox.sql_models.calculation import CalculationResponseModel

T = TypeVar("T", bound=BaseModel)


class ApplicationsResponseSpec(BaseModel):
    applications: list[ApplicationSpecWithCommands]


class CalculationsResponseSpec(BaseModel):
    calculations: list[CalculationResponseModel]


class DatasetResponseSpec(BaseModel):
    dataset: DatasetResponse


class DatasetCreateResponseSpec(BaseModel):
    qcrbox_dataset_id: str


class DatasetsResponseSpec(BaseModel):
    datasets: list[DatasetResponse]


class ErrorResponseSpec(BaseModel):
    code: int
    message: str


class QCrBoxResponseSpec(BaseModel, Generic[T]):
    """Pydantic model for QCrBox API response specification."""

    status: str
    message: str
    payload: T
    timestamp: str


class QCrBoxErrorResponseSpec(BaseModel):
    """Pydantic model for QCrBox API error response specification."""

    status: str
    error: ErrorResponseSpec
