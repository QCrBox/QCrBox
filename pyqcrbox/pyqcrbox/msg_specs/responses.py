from enum import StrEnum

from .base import QCrBoxBasePayload, QCrBoxGenericResponse


class ResponseStatusEnum(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


def success(*, response_to: str):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.SUCCESS)


def error(*, response_to: str, msg: str = ""):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.ERROR, msg=msg)


class HealthStatusEnum(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class PayloadForHealthCheckResponse(QCrBoxBasePayload):
    health_status: HealthStatusEnum


def health_check_healthy():
    return QCrBoxGenericResponse(
        response_to="health_check",
        status=ResponseStatusEnum.SUCCESS,
        msg="healthy",
        payload=PayloadForHealthCheckResponse(health_status=HealthStatusEnum.HEALTHY),
    )
