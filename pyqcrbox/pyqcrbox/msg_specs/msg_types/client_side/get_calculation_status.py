from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = [
    "GetCalculationStatusNATS",
    "CalculationStatusResponseNATS",
    "CloseInteractiveSessionNATS",
    "CloseInteractiveSessionResponse",
]


class GetCalculationStatusNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CalculationStatusResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str


class CloseInteractiveSessionNATS(QCrBoxPydanticBaseModel):
    session_id: str


class CloseInteractiveSessionResponse(QCrBoxPydanticBaseModel):
    session_id: str
    status: str
    output_dataset_id: str | None
    error_msg: str | None = None
