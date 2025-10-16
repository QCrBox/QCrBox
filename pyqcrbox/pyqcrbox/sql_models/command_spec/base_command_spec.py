from enum import Enum

from pydantic import Field

from pyqcrbox import settings

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpecDiscriminatedUnion

__all__ = []


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
    merge_cif_su: bool = False
    doi: str | None = None

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
