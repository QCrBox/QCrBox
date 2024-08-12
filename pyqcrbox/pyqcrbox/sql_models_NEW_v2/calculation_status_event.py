from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field, Relationship

from .base import QCrBoxBaseSQLModel

if TYPE_CHECKING:
    from .calculation_db import CalculationDB


class CalculationStatusEnum(StrEnum):
    SUBMITTED = "submitted"
    # CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CalculationStatusDetails(BaseModel):
    calculation_id: str
    status: CalculationStatusEnum
    stdout: str | None
    stderr: str | None
    extra_info: dict


class CalculationStatusEventDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "calculation_status_event"

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now)
    status: CalculationStatusEnum
    comment: str = ""

    calculation_id: int = Field(foreign_key="calculation.id")
    calculation: "CalculationDB" = Relationship(back_populates="status_events")
