from typing import Any

from pydantic import model_validator

from ..base import QCrBoxPydanticBaseModel


class BaseParameterSpec(QCrBoxPydanticBaseModel):
    name: str
    dtype: type
    description: str = ""
    required: bool = True
    default_value: Any

    @model_validator(mode="before")
    def store_default_value_if_provided(model_data: dict) -> dict:
        if "default_value" not in model_data or model_data["default_value"] == "<undefined>":
            model_data["required"] = True
            model_data["default_value"] = Ellipsis
        else:
            model_data["required"] = False

        return model_data
