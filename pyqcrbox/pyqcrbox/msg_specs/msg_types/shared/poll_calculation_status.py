from typing import Literal, Optional

from pydantic import BaseModel

from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxBasePayload, QCrBoxGenericResponse

__all__ = [
    "CalculationStatusDetails",
    "PollCalculationStatus",
    "PayloadForPollCalculationStatus",
    "ReportCalculationStatusDetails",
    "PayloadForReportCalculationStatusDetails",
]


class PayloadForPollCalculationStatus(QCrBoxBasePayload):
    correlation_id: str


class PollCalculationStatus(QCrBoxBaseAction):
    action: Literal["poll_calculation_status"]
    payload: PayloadForPollCalculationStatus


class CalculationStatusDetails(BaseModel):
    returncode: Optional[int]
    stdout: str
    stderr: str


class PayloadForReportCalculationStatusDetails(BaseModel):
    correlation_id: str
    calculation_status: CalculationStatusDetails


class ReportCalculationStatusDetails(QCrBoxGenericResponse):
    response_to: str = Literal[PollCalculationStatus.action_name]
    status: str = "ok"
    payload: PayloadForReportCalculationStatusDetails
