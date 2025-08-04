from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = [
    "EndCommandRequestNATS",
    "EndCommandResponseNATS",
]


class EndCommandRequestNATS(QCrBoxPydanticBaseModel):
    calculation_id: str


class EndCommandResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    status: str
    output_dataset_id: str | None
    error_msg: str | None = None
