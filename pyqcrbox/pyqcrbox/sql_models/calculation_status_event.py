from enum import StrEnum

from pydantic import BaseModel


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
    stdout: str = ""
    stderr: str = ""
    extra_info: dict = {}
