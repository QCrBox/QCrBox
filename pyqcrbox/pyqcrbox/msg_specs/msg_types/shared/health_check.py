from typing import Literal

from pyqcrbox.msg_specs.base import QCrBoxBaseAction

__all__ = ["HealthCheck"]


class HealthCheck(QCrBoxBaseAction):
    action: Literal["health_check"]
