from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


def set_timestamp_to_utc_now() -> str:
    """Return datetime.now() in UTC.

    Returns
    -------
    str
        A timestamp in ISO format for the current time in UTC.

    """
    return datetime.now(UTC).isoformat()


class CalculationStatusEnum(StrEnum):
    """Enumeration of possible calculation statuses.

    Attributes
    ----------
    SUBMITTED
        Calculation has been submitted and is awaiting processing.
    RUNNING
        Calculation is currently running.
    SUCCESSFUL
        Calculation completed successfully.
    FAILED
        Calculation failed to complete.
    CANCELLED
        Calculation was cancelled before completion.
    UNKNOWN
        Calculation status is unknown.

    """

    SUBMITTED = "submitted"
    # CHECKING_CLIENT_AVAILABILITY = "checking_client_availability"
    RUNNING = "running"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CalculationStatusDetails(BaseModel):
    """Details about the status of a calculation event.

    Attributes
    ----------
    calculation_id : str
        Unique identifier for the calculation.
    status : CalculationStatusEnum
        Current status of the calculation.
    stdout : str | None
        Standard output from the calculation process (default empty string).
    stderr : str | None
        Standard error output from the calculation process (default empty string).
    extra_info : dict
        Additional information related to the calculation event.
    timestamp : datetime
        Timestamp of the status event (UTC).

    """

    calculation_id: str
    status: CalculationStatusEnum
    stdout: str | None = ""
    stderr: str | None = ""
    output_dataset_id: str | None = None
    extra_info: dict = {}
    timestamp: str = Field(default_factory=set_timestamp_to_utc_now)

    @field_validator("stdout", "stderr", mode="before")
    @classmethod
    def none_to_empty_str(cls, v):
        return "" if v is None else v
