from typing import Any

from pydantic import model_validator

from ..base import QCrBoxPydanticBaseModel

SENTINEL_UNDEFINED = "<undefined>"


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: type
    required: bool = True
    default_value: Any
    description: str = ""

    @model_validator(mode="before")
    @classmethod
    def store_default_value_if_provided(cls, model_data: dict) -> dict:
        model_data = model_data.copy()

        if "default_value" not in model_data or model_data["default_value"] == SENTINEL_UNDEFINED:
            model_data["required"] = True
            model_data["default_value"] = SENTINEL_UNDEFINED
        else:
            model_data["required"] = False

        return model_data
