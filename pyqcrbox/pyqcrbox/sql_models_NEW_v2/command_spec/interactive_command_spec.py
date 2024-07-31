from typing import Any, Literal

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpecDiscriminatedUnion
from .base_command_spec import BaseCommandSpec
from .non_interactive_command_spec import NonInteractiveCommandSpec


class InteractiveLifecycleSteps(QCrBoxPydanticBaseModel):
    prepare: NonInteractiveCommandSpec
    run: NonInteractiveCommandSpec
    finalise: NonInteractiveCommandSpec
    toparams: NonInteractiveCommandSpec


class InteractiveCommandSpec(BaseCommandSpec):
    implemented_as: Literal["interactive"] = "interactive"
    parameters: list[ParameterSpecDiscriminatedUnion]
    interactive_lifecycle: InteractiveLifecycleSteps
    non_interactive_equivalent: NonInteractiveCommandSpec
