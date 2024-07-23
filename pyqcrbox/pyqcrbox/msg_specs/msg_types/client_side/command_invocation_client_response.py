from pyqcrbox.sql_models_NEW_v2 import QCrBoxPydanticBaseModel

__all__ = ["CommandInvocationClientResponseNATS"]


class CommandInvocationClientResponseNATS(QCrBoxPydanticBaseModel):
    calculation_id: str
    application_slug: str
    application_version: str
    client_id: str
    client_is_available: bool
    private_inbox_prefix: str
