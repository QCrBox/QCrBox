from pyqcrbox.sql_models_NEW_v2 import QCrBoxPydanticBaseModel

__all__ = ["GetCalculationStatusNATS", "CalculationStatusResponseNATS"]


class GetCalculationStatusNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CalculationStatusResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str
