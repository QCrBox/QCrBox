from pyqcrbox.sql_models.qcrbox_base_models import QCrBoxPydanticBaseModel

__all__ = ["GetCalculationStatusNATS", "CalculationStatusResponseNATS"]


class GetCalculationStatusNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class CalculationStatusResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str
