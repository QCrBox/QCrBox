from enum import Enum

from ..base import QCrBoxPydanticBaseModel
from ..parameter_spec import ParameterSpecDiscriminatedUnion

__all__ = []


class ImplementedAs(str, Enum):
    cli = "cli_command"
    python_callable = "python_callable"
    interactive = "interactive"


class BaseCommandSpec(QCrBoxPydanticBaseModel):
    name: str
    description: str = ""
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
        return self.implemented_as == ImplementedAs.interactive

    @property
    def parameter_default_values(self):
        return {param.name: param.default_value for param in self.parameters if not param.required}
