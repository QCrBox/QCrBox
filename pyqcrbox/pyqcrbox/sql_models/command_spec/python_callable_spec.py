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


class PythonCallableParameterValidator:
    """Class for validating a PythonCallable parameters."""

    def __init__(self, fn_signature: inspect.Signature):
        self.fn_signature = fn_signature
        self.fn_params = {p.name: get_param_spec_from_signature_param(p) for p in self.fn_signature.parameters.values()}
        logger.debug(f"PythonCallable: fn_signature {self.fn_signature}")
        logger.debug(f"PythonCallable: fn_params {self.fn_params}")

    def validate(self, param_spec: dict | ParameterSpecDiscriminatedUnion):
        """Validate a parameter against its Python callable."""
        param_spec = parameter_spec_adapter.validate_python(param_spec)

        if param_spec.name not in self.fn_params:
            raise ValueError(f"Parameter {param_spec.name!r} not present in function signature")

        fn_param = self.fn_params[param_spec.name]
        if fn_param is None:
            raise MissingTypeAnnotation(f"Missing type annotation for parameter: {param_spec.name!r}")

        if not param_spec.dtype_is_compatible_with(fn_param.dtype):
            raise ValueError(
                f"Parameter dtype mismatch: {param_spec.dtype!r} is not compatible with {fn_param.dtype!r}"
            )


class PythonCallableSpec(BaseCommandSpec):
    """Pydantic model for specifying PythonCallable commands.

    Attributes
    ----------
    implemented_as : str
        The implemented as method, it being a python_callable.
    import_path : str
        The path to the Python source script to import, containing the callable.
    callable_name : str
        The name of the callable Python function. If this is not provided, it
        is assumed to be the same as the PythonCallable command name.

    """

    implemented_as: Literal["python_callable"] = "python_callable"  # type: ignore
    import_path: str
    callable_name: str | None = None

    @model_validator(mode="after")
    def validate_parameters_against_function_signature(model_data: "PythonCallableSpec") -> "PythonCallableSpec":
        """Validate the parameters in the application spec against the callable function."""
        if not model_data.callable_name:
            raise ValueError("The name of the python callable function has has not been set")

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
        fn_validator = PythonCallableParameterValidator(fn_signature)

        for p in model_data.parameters:
            try:
                fn_validator.validate(p)
            except MissingTypeAnnotation:
                logger.warning(f"No type annotation present for parameter {p.name!r} - skipping validation.")

        # Output filenames are injected into the callable as string keyword
        # arguments under the output's name, so the signature must accept them.
        for output in model_data.outputs:
            if output.name not in fn_validator.fn_params:
                raise ValueError(f"Output {output.name!r} not present in function signature")
            fn_output_param = fn_validator.fn_params[output.name]
            if fn_output_param is not None and fn_output_param.dtype != "str":
                raise ValueError(
                    f"Output {output.name!r} must be annotated as 'str' in the function signature "
                    f"(the injected value is the output filename), got {fn_output_param.dtype!r}"
                )

        return model_data

    @model_validator(mode="before")
    @classmethod
    def set_name_and_callable_name_if_missing(cls, model_data: dict) -> dict:
        """If `callable_name` is not explicitly provided, assume it is the same as the command name and vice versa."""
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
