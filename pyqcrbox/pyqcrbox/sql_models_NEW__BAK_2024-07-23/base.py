from pydantic import BaseModel, ConfigDict

__all__ = ["QCrBoxPydanticBaseModel"]


class QCrBoxPydanticBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
