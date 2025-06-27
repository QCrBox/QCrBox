from enum import StrEnum

from pydantic import BaseModel, field_validator


class CalculationStatusEnum(StrEnum):
    SUBMITTED = "submitted"
    # CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CalculationStatusDetails(BaseModel):
    calculation_id: str
    status: CalculationStatusEnum
    stdout: str | None = ""
    stderr: str | None = ""
    extra_info: dict = {}

    @field_validator("stdout", "stderr", mode="before")
    @classmethod
    def none_to_empty_str(cls, v):
        return "" if v is None else v
