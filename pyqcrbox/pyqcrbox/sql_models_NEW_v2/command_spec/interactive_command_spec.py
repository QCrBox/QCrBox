from typing import Any, Literal

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpec
from .base_command_spec import BaseCommandSpec
from .non_interactive_command_spec import NonInteractiveCommandSpec


class InteractiveLifecycleSteps(QCrBoxPydanticBaseModel):
    prepare: Any
    run: Any
    finalise: Any
    toparams: Any


class InteractiveCommandSpec(BaseCommandSpec):
    implemented_as: Literal["interactive"] = "interactive"
    parameters: list[ParameterSpec]
    interactive_lifecycle: InteractiveLifecycleSteps
    non_interactive_equivalent: NonInteractiveCommandSpec
