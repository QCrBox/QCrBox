from datetime import datetime
from typing import Any

from pydantic import Field

from pyqcrbox.sql_models.base import QCrBoxPydanticBaseModel
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusEventDB


class CalculationNatsBase(QCrBoxPydanticBaseModel):
    calculation_id: str
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]


class CalculationNatsResponseModel(CalculationNatsBase):
    status: str


class CalculationNatsDB(CalculationNatsBase):
    timestamp: datetime = Field(default_factory=datetime.now)
    status_events: list[CalculationStatusEventDB] = Field(default_factory=list)
    application_id: int | None = None
    command_id: int | None = None

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["timestamp"] = self.timestamp.isoformat()
        return data
