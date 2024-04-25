from enum import StrEnum

from .base import QCrBoxGenericResponse


class ResponseStatusEnum(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


def success(*, response_to: str):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.SUCCESS)


def error(*, response_to: str):
    return QCrBoxGenericResponse(response_to=response_to, status=ResponseStatusEnum.ERROR)
