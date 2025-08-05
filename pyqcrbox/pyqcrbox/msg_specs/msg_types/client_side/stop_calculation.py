from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = [
    "StopRunningCalculationMsg",
    "StoppedCalculationResponseMsg",
]


class StopRunningCalculationMsg(QCrBoxPydanticBaseModel):
    calculation_id: str


class StoppedCalculationResponseMsg(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str
    output_dataset_id: str | None
    error_msg: str | None = None
