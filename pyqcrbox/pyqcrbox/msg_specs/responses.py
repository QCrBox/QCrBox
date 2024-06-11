from enum import StrEnum
from typing import Optional

from .base import QCrBoxBasePayload, QCrBoxGenericResponse


class ResponseStatusEnum(StrEnum):
    OK = "ok"
    SUCCESS = "success"
    ERROR = "error"


def ok(*, response_to: str, msg: str = "", payload: Optional[QCrBoxBasePayload | dict] = None):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.OK, msg=msg, payload=payload)


def success(*, response_to: str, msg: str = "", payload: Optional[QCrBoxBasePayload | dict] = None):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.SUCCESS, msg=msg, payload=payload)


def error(*, response_to: str, msg: str = "", payload: Optional[QCrBoxBasePayload | dict] = None):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.ERROR, msg=msg, payload=payload)


class HealthStatusEnum(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class PayloadForHealthCheckResponse(QCrBoxBasePayload):
    health_status: HealthStatusEnum


class QCrBoxHealthCheckResponse(QCrBoxGenericResponse):
    payload: PayloadForHealthCheckResponse


def health_check_healthy() -> QCrBoxHealthCheckResponse:
    return QCrBoxHealthCheckResponse(
        response_to="health_check",
        status=ResponseStatusEnum.SUCCESS,
        msg="healthy",
        payload=PayloadForHealthCheckResponse(health_status=HealthStatusEnum.HEALTHY),
    )
