import inspect
from pydantic import BaseModel, Extra
from typing import Literal, Optional

from .sql_models import QCrBoxApplicationCreate, QCrBoxCommandCreate, QCrBoxCalculationCreate


class QCrBoxBaseMessage(BaseModel):
    # model_config = ConfigDict(extra='forbid')
    class Config:
        extra = Extra.forbid


class QCrBoxBaseAction(QCrBoxBaseMessage):
    action: str
    payload: BaseModel


class RegisterApplication(QCrBoxBaseAction):
    action: Literal["register_application"]
    payload: QCrBoxApplicationCreate


class RegisterCommand(QCrBoxBaseAction):
    action: Literal["register_command"]
    payload: QCrBoxCommandCreate


class InvokeCommand(QCrBoxBaseAction):
    action: Literal["invoke_command"]
    payload: QCrBoxCalculationCreate


class ExecuteCalculationPayload(BaseModel):
    command_id: int
    calculation_id: int
    arguments: dict
    container_qcrbox_id: Optional[str] = None


class ExecuteCalculation(QCrBoxBaseAction):
    action: Literal["execute_calculation"]
    payload: ExecuteCalculationPayload


class GetCalculationStatusDetailsPayload(BaseModel):
    calculation_id: int


class GetCalculationStatusDetails(QCrBoxBaseAction):
    action: Literal["get_calculation_status_details"]
    payload: GetCalculationStatusDetailsPayload


class GetContainerStatusPayload(BaseModel):
    container_id: int


class GetContainerStatus(QCrBoxBaseAction):
    action: Literal["get_container_status"]
    payload: GetContainerStatusPayload


class QCrBoxGenericResponse(QCrBoxBaseMessage):
    response_to: str
    status: str
    msg: Optional[str] = None
    payload: Optional[dict] = None


class RegisterApplicationPayload(BaseModel):
    application_id: int
    container_id: int


class RegisterApplicationResponse(QCrBoxGenericResponse):
    response_to: Literal["register_application"]
    status: str
    msg: Optional[str] = None
    payload: Optional[RegisterApplicationPayload] = None


def represents_valid_qcrbox_message(cls):
    return (
        inspect.isclass(cls) and issubclass(cls, QCrBoxBaseMessage) and cls not in (QCrBoxBaseMessage, QCrBoxBaseAction)
    )


def represents_valid_qcrbox_action(cls):
    return inspect.isclass(cls) and issubclass(cls, QCrBoxBaseAction) and cls is not QCrBoxBaseAction


def represents_valid_qcrbox_response(cls):
    return inspect.isclass(cls) and issubclass(cls, QCrBoxGenericResponse)


# Generate a list of all classes representing valid QCrBox action messages
VALID_QCRBOX_MESSAGES = [cls for cls in locals().values() if represents_valid_qcrbox_message(cls)]
VALID_QCRBOX_ACTIONS = [cls for cls in locals().values() if represents_valid_qcrbox_action(cls)]
VALID_QCRBOX_RESPONSES = [cls for cls in locals().values() if represents_valid_qcrbox_response(cls)]

# Ensure that QCrBoxGenericResponse comes last because it is the last fallback
# after trying the more specific message types.
VALID_QCRBOX_MESSAGES.remove(QCrBoxGenericResponse)
VALID_QCRBOX_MESSAGES += [QCrBoxGenericResponse]
VALID_QCRBOX_RESPONSES.remove(QCrBoxGenericResponse)
VALID_QCRBOX_RESPONSES += [QCrBoxGenericResponse]
