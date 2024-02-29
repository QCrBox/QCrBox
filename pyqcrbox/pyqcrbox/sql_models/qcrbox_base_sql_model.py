from pydantic import ConfigDict
from sqlmodel import SQLModel


class QCrBoxBaseSQLModel(SQLModel):
    """
    Base class for QCrBox SQL models. This allows us to add custom
    tweaks or QCrBox-specific functionality as and when needed.
    """

    model_config = ConfigDict(extra="forbid")
