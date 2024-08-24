import importlib
import inspect
from typing import Literal

from pydantic import model_validator

from pyqcrbox.logging import logger

from ..parameter_spec import ParameterSpecDiscriminatedUnion, get_param_spec_from_signature_param
from ..parameter_spec.parameter_spec import parameter_spec_adapter
from .base_command_spec import BaseCommandSpec

__all__ = ["PythonCallableSpec"]


class MissingTypeAnnotation(Exception):
    pass


class ParameterValidator:
    def __init__(self, fn_signature: inspect.Signature):
        self.fn_signature = fn_signature
        self.fn_params = {p.name: get_param_spec_from_signature_param(p) for p in self.fn_signature.parameters.values()}

    def validate(self, param_spec: dict | ParameterSpecDiscriminatedUnion):
        param_spec = parameter_spec_adapter.validate_python(param_spec)

        if param_spec.name not in self.fn_params:
            raise ValueError(f"Parameter {param_spec.name!r} not present in function signature")

        fn_param = self.fn_params[param_spec.name]
        if fn_param is None:
            raise MissingTypeAnnotation(f"Missing type annotation for parameter: {param_spec.name!r}")
        if param_spec.dtype != fn_param.dtype:
            raise ValueError(f"Parameter dtype mismatch: {param_spec.dtype} != {fn_param.dtype}")

        if param_spec.required != fn_param.required:
            raise ValueError(f"Mismatch in parameter definitions: {param_spec!r} != {fn_param!r}")
        #
        # if not param_spec.required and param_spec.default_value != fn_param.default_value:
        #     raise ValueError(f"Mismatch in parameter definitions: {param_spec!r} != {fn_param!r}")


class PythonCallableSpec(BaseCommandSpec):
    implemented_as: Literal["python_callable"] = "python_callable"
    import_path: str
    callable_name: str | None = None

    # @model_validator(mode="before")
    # def validate_parameters_against_function_signature(model_data):
    #     # module = importlib.import_module(model_data["import_path"])
    #     # fn = getattr(module, model_data["callable_name"])
    #     # signature = inspect.signature(fn)
    #     # parameters = [get_param_spec_from_signature_param(p) for p in signature.parameters.values()]
    #     parameters = []
    #
    #     if "parameters" not in model_data:
    #         model_data["parameters"] = parameters
    #     else:
    #         raise NotImplementedError("TODO: validate given parameters against function signature")
    #
    #     return model_data

    @model_validator(mode="after")
    def validate_parameters_against_function_signature(model_data):
        try:
            module = importlib.import_module(model_data.import_path)
        except ImportError as exc:
            logger.warning(
                f"Failed to import module: {model_data.import_path!r}. "
                f"Skipping validation of parameters against function signature. "
                f"The original error was: {exc}"
            )
            return model_data

        fn = getattr(module, model_data.callable_name)
        fn_signature = inspect.signature(fn)
        # fn_params = [get_param_spec_from_signature_param(p) for p in fn_signature.parameters.values()]

        fn_validator = ParameterValidator(fn_signature)
        for p in model_data.parameters:
            try:
                fn_validator.validate(p)
            except MissingTypeAnnotation:
                logger.warning(f"No type annotation present for parameter {p.name!r} - skipping validation.")

        return model_data

    @model_validator(mode="before")
    @classmethod
    def set_name_and_callable_name_if_missing(cls, model_data: dict) -> dict:
        """
        If `callable_name` is not explicitly provided, assume it is the same as the command name and vice versa.
        """
        match model_data.get("name"), model_data.get("callable_name"):
            case None, None:
                raise ValueError("The fields 'name' and 'callable_name' cannot both be missing")
            case _, None:
                model_data["callable_name"] = model_data["name"]
            case None, _:
                model_data["name"] = model_data["callable_name"]
            case _:
                pass

        if "." in model_data["callable_name"]:
            raise ValueError("Qualified names (containing dots) are not supported yet")

        return model_data
