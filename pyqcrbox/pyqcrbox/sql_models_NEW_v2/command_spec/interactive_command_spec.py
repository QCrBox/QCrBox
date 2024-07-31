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
            cmd_data.setdefault("name", f"__interactive_{key}")
        return model_data

    @property
    def commands(self):
        return [getattr(self, name) for name in self.model_fields.keys()]


class InteractiveCommandSpec(BaseCommandSpec):
    implemented_as: Literal["interactive"] = "interactive"
    parameters: list[ParameterSpecDiscriminatedUnion]
    interactive_lifecycle: InteractiveLifecycleSteps
    non_interactive_equivalent: NonInteractiveCommandSpec

    @model_validator(mode="before")
    @classmethod
    def set_parameters_for_interactive_lifecycle_commands(cls, model_data: dict) -> dict:
        if "interactive_lifecycle" not in model_data:
            raise ValueError("Field required: 'interactive_lifecycle'")

        params_lookup_by_name = {param["name"]: param for param in model_data["parameters"]}
        for cmd_data in model_data["interactive_lifecycle"].values():
            used_basecommand_parameters = cmd_data.pop("used_basecommand_parameters", [])
            cmd_data["parameters"] = [params_lookup_by_name[name] for name in used_basecommand_parameters]

        return model_data
