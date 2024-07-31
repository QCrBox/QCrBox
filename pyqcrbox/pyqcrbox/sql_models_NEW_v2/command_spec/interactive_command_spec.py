from typing import Literal

from pydantic import model_validator

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpecDiscriminatedUnion
from .base_command_spec import BaseCommandSpec
from .non_interactive_command_spec import NonInteractiveCommandSpec


class InteractiveLifecycleSteps(QCrBoxPydanticBaseModel):
    prepare: NonInteractiveCommandSpec
    run: NonInteractiveCommandSpec
    finalise: NonInteractiveCommandSpec
    toparams: NonInteractiveCommandSpec

    @model_validator(mode="before")
    @classmethod
    def set_missing_names_for_lifecycle_step_commands(cls, model_data: dict) -> dict:
        for key, cmd_data in model_data.items():
            cmd_data.setdefault("name", f"{key}__interactive")
        return model_data


class InteractiveCommandSpec(BaseCommandSpec):
    implemented_as: Literal["interactive"] = "interactive"
    parameters: list[ParameterSpecDiscriminatedUnion]
    interactive_lifecycle: InteractiveLifecycleSteps
    non_interactive_equivalent: NonInteractiveCommandSpec
