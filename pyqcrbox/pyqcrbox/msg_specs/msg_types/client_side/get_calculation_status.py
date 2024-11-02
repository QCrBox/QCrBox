from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = ["GetCalculationStatusNATS", "CalculationStatusResponseNATS", "CloseInteractiveSessionNATS"]


class GetCalculationStatusNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CalculationStatusResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str


class CloseInteractiveSessionNATS(QCrBoxPydanticBaseModel):
    session_id: str


class CloseInteractiveSessionResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str
