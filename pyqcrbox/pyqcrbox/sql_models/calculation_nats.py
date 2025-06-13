from datetime import datetime
from typing import Any

from pydantic import Field, computed_field

from pyqcrbox.sql_models.base import QCrBoxPydanticBaseModel
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusEnum, CalculationStatusEventDB


class CalculationNatsBase(QCrBoxPydanticBaseModel):
    """Base dataclass for calculation metadata."""

    calculation_id: str
    application_slug: str
    application_version: str
    command_name: str
    arguments: dict[str, Any]


class CalculationNatsResponseModel(CalculationNatsBase):
    """Calculation response model, for API responses."""

    status: str


class CalculationNatsDB(CalculationNatsBase):
    """Dataclass containing metadata about a calculation, used for NATS."""

    timestamp: datetime = Field(default_factory=datetime.now)
    status_events: list[CalculationStatusEventDB] = Field(default_factory=list)
    application_id: int | None = None
    command_id: int | None = None

    @computed_field(return_type=str)
    @property
    def status(self):
        if len(self.status_events) == 0:
            return CalculationStatusEnum.UNKNOWN
        return self.status_events[-1].status

    def to_response_model(self) -> CalculationNatsResponseModel:
        data = self.model_dump(
            include=[
                "calculation_id",
                "status",
                "application_slug",
                "application_version",
                "command_name",
                "arguments",
            ],
        )

        return CalculationNatsResponseModel(**data)
