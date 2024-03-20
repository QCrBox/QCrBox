from typing import Literal

from pyqcrbox.msg_specs.base import QCrBoxActionBasePayload, QCrBoxBaseAction

__all__ = ["PollCalculationStatus", "PayloadForPollCalculationStatus"]


class PayloadForPollCalculationStatus(QCrBoxActionBasePayload):
    correlation_id: str


class PollCalculationStatus(QCrBoxBaseAction):
    action: Literal["poll_calculation_status"]
    payload: PayloadForPollCalculationStatus
