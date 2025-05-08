import datetime
from typing import Generic, TypeVar

from litestar.response import Response
from pydantic import BaseModel

from pyqcrbox.sql_models.application_spec import ApplicationSpecWithCommands
from pyqcrbox.sql_models.calculation import CalculationResponseModel

T = TypeVar("T", bound=BaseModel)


class CalculationsResponse(BaseModel):
    calculations: list[CalculationResponseModel]


class ApplicationsResponse(BaseModel):
    applications: list[ApplicationSpecWithCommands]


class QCrBoxResponseSpec(BaseModel, Generic[T]):
    """Pydantic model for QCrBox API response specification."""

    status: str
    message: str
    payload: T
    timestamp: str


class QCrBoxResponse(Response):
    """Custom response class for QCrBox API responses.

    This class sets the default content type to JSON and adds a timestamp.
    """

    def __init__(self, content: dict, *args, **kwargs):
        content.setdefault("timestamp", datetime.datetime.now(tz=datetime.UTC).isoformat() + "Z")
        super().__init__(content, media_type="application/json", *args, **kwargs)
