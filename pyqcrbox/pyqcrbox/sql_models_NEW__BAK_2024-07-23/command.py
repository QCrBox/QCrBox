import importlib
import inspect
from enum import Enum
from typing import Annotated, Any, Literal, Self, Union

from pydantic import Field, Tag, model_validator

from .base import QCrBoxPydanticBaseModel
from .call_pattern import CallPattern
from .parameter import ParameterSpec

__all__ = ["CommandSpec"]


class ImplementedAs(str, Enum):
    cli = "CLI"
    python_callable = "python_callable"
    interactive = "interactive"


class CommandSpecBase(QCrBoxPydanticBaseModel):
    name: str
    description: str = ""
    merge_cif_su: bool = False
    implemented_as: ImplementedAs
    doi: str | None = None

    @property
    def is_python_callable(self):
        return self.implementation.implemented_as == ImplementedAs.python_callable

    @property
    def is_cli_command(self):
        return self.implementation.implemented_as == ImplementedAs.cli_command


class CLICommandSpec(CommandSpecBase):
    implemented_as: Literal["cli_command"]
    call_pattern: CallPattern
    parameters: list[ParameterSpec]


class PythonCallableSpec(CommandSpecBase):
    implemented_as: Literal["python_callable"]
    import_path: str
    callable_name: str | None = None
    parameters: list[ParameterSpec]

    @model_validator(mode="before")
    def validate_parameters_against_function_signature(model_data):
        module = importlib.import_module(model_data["import_path"])
        fn = getattr(module, model_data["callable_name"])
        signature = inspect.signature(fn)
        parameters = [ParameterSpec.from_function_signature_param(*p) for p in signature.parameters.items()]

        if "parameters" not in model_data:
            model_data["parameters"] = parameters
        else:
            raise NotImplementedError("TODO: validate given parameters against function signature")

        return model_data

    @model_validator(mode="before")
    def set_callable_name_if_not_provided(model_data) -> Self:
        """
        If `callable_name` is not explicitly provided, assume it is the same as the command name.
        """
        if "callable_name" not in model_data:
            model_data["callable_name"] = model_data["name"]

        if "." in model_data["callable_name"]:
            raise ValueError("Qualified names (containing dots) are not supported yet")

        return model_data


class InteractiveLifecycleSteps(QCrBoxPydanticBaseModel):
    prepare: Any
    run: Any
    finalise: Any
    toparams: Any


NonInteractiveCommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
    ],
    Field(discriminator="implemented_as"),
    Field(title="name", default="foo")
]


class InteractiveCommandSpec(CommandSpecBase):
    implemented_as: Literal["interactive"]
    parameters: list[ParameterSpec]
    interactive_lifecycle: InteractiveLifecycleSteps
    non_interactive_equivalent: NonInteractiveCommandSpec


CommandSpec = Annotated[
    Union[
        Annotated[CLICommandSpec, Tag("cli_command")],
        Annotated[PythonCallableSpec, Tag("python_callable")],
        Annotated[InteractiveCommandSpec, Tag("interactive")],
    ],
    Field(discriminator="implemented_as"),
]
