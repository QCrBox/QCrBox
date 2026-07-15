from enum import Enum

from pydantic import Field, model_validator

from pyqcrbox import settings

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpecDiscriminatedUnion
from .output_spec import OutputCifSpec, OutputSpecDiscriminatedUnion

__all__ = []

# Output dtypes must not appear in the `parameters:` section
_OUTPUT_DTYPES = (
    "QCrBox.output_cif",
    "QCrBox.output_path",
    "QCrBox.output_text",
    "QCrBox.output_image",
    "QCrBox.output_html",
    "QCrBox.output_interactive_structure",
    "QCrBox.output_interactive_graph",
)


class ImplementedAs(str, Enum):
    cli_command = "cli_command"
    python_callable = "python_callable"
    interactive_session = "interactive_session"


class BaseCommandSpec(QCrBoxPydanticBaseModel):
    """Base model specification for a command.

    This is used for both non-interactive commands as well as interactive
    commands and the commands making up the interactive lifecycle.

    Attributes
    ----------
    name : str
        The name of the command
    description : str
        A description  of the command.
    implemented_as : ImplementedAs
        The type of command this is, e.g. interactive_session, CLICommand or
        PythonCallable.
    parameters : list[ParameterSpecDiscriminatedUnion]
        A list of parameters for the command, represented as parameter
        specifications.
    merge_cif_su : bool
        Whether to merge the CIF SU or not??
    doi : str
        Data object identifier for this command.

    Properties
    ----------
    is_python_callable : bool
        Whether this command is implemented as PythonCallable.
    is_cli_command : bool
        Whether this command is implemented as CLICommand.
    is_interactive : bool
        Whether this command is an interactive session.
    parameter_default_values : dict
        A mapping of parameter name to the default value for that parameter.
        This only includes non-required parameters.

    """

    name: str = Field(max_length=settings.db.max_text_length)
    description: str | None = Field(default=None, max_length=settings.db.max_desc_length)
    implemented_as: ImplementedAs
    parameters: list[ParameterSpecDiscriminatedUnion]
    outputs: list[OutputSpecDiscriminatedUnion] = []
    merge_cif_su: bool = False
    doi: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_output_dtypes_in_parameters(cls, data):
        if isinstance(data, dict):
            for param in data.get("parameters") or []:
                dtype = param.get("dtype") if isinstance(param, dict) else getattr(param, "dtype", None)
                if dtype in _OUTPUT_DTYPES:
                    name = param.get("name") if isinstance(param, dict) else getattr(param, "name", "?")
                    raise ValueError(
                        f"Parameter {name!r} has output dtype {dtype!r}: command outputs are declared "
                        "in the command's 'outputs:' section, not in 'parameters:'"
                    )
        return data

    @model_validator(mode="after")
    def verify_outputs_are_consistent(self):
        if isinstance(self.outputs, dict) or isinstance(self.parameters, dict):
            # Response models carry parameters/outputs as {name: dump} dicts
            return self
        output_names = [output.name for output in self.outputs]
        parameter_names = [param.name for param in self.parameters]
        clashes = set(output_names) & set(parameter_names)
        if clashes:
            raise ValueError(f"Output names clash with parameter names: {sorted(clashes)!r}")
        if len(output_names) != len(set(output_names)):
            raise ValueError(f"Output names must be unique, got: {output_names!r}")
        cif_outputs = [output for output in self.outputs if isinstance(output, OutputCifSpec)]
        if len(cif_outputs) > 1:
            raise ValueError("A command can declare at most one 'QCrBox.output_cif' output")
        return self

    @property
    def output_cif_spec(self) -> OutputCifSpec | None:
        """The command's pipeline-continuing output CIF spec, if declared."""
        return next((output for output in self.outputs if isinstance(output, OutputCifSpec)), None)

    @property
    def is_python_callable(self) -> bool:
        return self.implemented_as == ImplementedAs.python_callable

    @property
    def is_cli_command(self) -> bool:
        return self.implemented_as == ImplementedAs.cli_command

    @property
    def is_interactive(self) -> bool:
        return self.implemented_as == ImplementedAs.interactive_session

    @property
    def is_non_interactive(self) -> bool:
        return self.implemented_as != ImplementedAs.interactive_session

    @property
    def parameter_default_values(self):
        # For now, we have removed this functionality as all parameters are required in a command
        # return {param.name: param.default_value for param in self.parameters if not param.required}
        return {}

    def get_parameter_by_name(self, param_name) -> ParameterSpecDiscriminatedUnion:
        # TODO: handle case where parameter is not found
        return next(param for param in self.parameters if param.name == param_name)
