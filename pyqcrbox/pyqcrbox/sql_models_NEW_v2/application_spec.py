from pathlib import Path

import yaml
from pydantic import PrivateAttr, field_validator

from .base import QCrBoxPydanticBaseModel
from .cif_entry_set import CifEntrySet
from .command_spec import CommandSpec

__all__ = ["ApplicationSpec"]


class ApplicationSpecBase(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: str | None = None
    url: str | None = None
    email: str | None = None
    doi: str | None = None


class ApplicationSpec(ApplicationSpecBase):
    commands: list[CommandSpec] = []
    cif_entry_sets: list[CifEntrySet] = []

    _commands_by_name: dict[str, CommandSpec] = PrivateAttr(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        self._commands_by_name = {cmd.name: cmd for cmd in self.commands}

    # @property
    # def cmds_by_name(self) -> Namespace:
    #     return Namespace(**self._commands_by_name)

    @property
    def command_names(self) -> list[str]:
        return list(self._commands_by_name.keys())

    @field_validator("commands")
    @classmethod
    def verify_command_names_are_unique(cls, value: list[CommandSpec]) -> list[CommandSpec]:
        command_names = [c.name for c in value]
        if len(command_names) != len(set(command_names)):
            raise ValueError("Command names must be unique")
        return value

    @classmethod
    def from_yaml_file(cls, file_path: str | Path):
        file_path = Path(file_path)
        return cls(**yaml.safe_load(file_path.open()))

    def get_command_by_name(self, cmd_name: str) -> CommandSpec:
        return self._commands_by_name[cmd_name]
