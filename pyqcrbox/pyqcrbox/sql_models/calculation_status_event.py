from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Union

from sqlmodel import Field, Relationship

from .qcrbox_base_models import QCrBoxBaseSQLModel

if TYPE_CHECKING:
    from .calculation import CalculationDB


class CalculationStatusEnum(StrEnum):
    RECEIVED = "received"
    CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CalculationStatusEventDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "calculation_status_event"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    status: CalculationStatusEnum = CalculationStatusEnum.RECEIVED
    comment: str = ""

    calculation_id: int | None = Field(default=None, foreign_key="calculation.id")
    calculation: Union["CalculationDB", None] = Relationship(back_populates="status_events")
