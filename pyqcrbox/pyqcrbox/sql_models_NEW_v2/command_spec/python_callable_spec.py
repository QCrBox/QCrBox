from typing import Literal

from pydantic import model_validator

from ..parameter_spec import ParameterSpec
from .base_command_spec import BaseCommandSpec


class PythonCallableSpec(BaseCommandSpec):
    implemented_as: Literal["python_callable"] = "python_callable"
    import_path: str
    callable_name: str | None = None
    parameters: list[ParameterSpec]

    @model_validator(mode="before")
    def validate_parameters_against_function_signature(model_data):
        # module = importlib.import_module(model_data["import_path"])
        # fn = getattr(module, model_data["callable_name"])
        # signature = inspect.signature(fn)
        # parameters = [get_param_spec_from_function_signature_param(p) for p in signature.parameters.values()]
        parameters = []

        if "parameters" not in model_data:
            model_data["parameters"] = parameters
        else:
            raise NotImplementedError("TODO: validate given parameters against function signature")

        return model_data

    @model_validator(mode="before")
    @classmethod
    def set_callable_name_if_not_provided(cls, model_data: dict) -> dict:
        """
        If `callable_name` is not explicitly provided, assume it is the same as the command name.
        """
        if "callable_name" not in model_data:
            model_data["callable_name"] = model_data["name"]

        if "." in model_data["callable_name"]:
            raise ValueError("Qualified names (containing dots) are not supported yet")

        return model_data
