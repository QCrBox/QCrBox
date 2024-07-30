from enum import Enum

from pyqcrbox.sql_models_NEW_v2.base import QCrBoxPydanticBaseModel

__all__ = []


class ImplementedAs(str, Enum):
    cli = "cli_command"
    python_callable = "python_callable"
    interactive = "interactive"


class BaseCommandSpec(QCrBoxPydanticBaseModel):
    name: str
    description: str = ""
    merge_cif_su: bool = False
    implemented_as: ImplementedAs
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
