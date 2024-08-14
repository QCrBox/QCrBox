import sys

from collections import UserDict
from datetime import datetime
from pathlib import Path
from typing import Self

import yaml
from pydantic import Extra, PrivateAttr, field_validator, model_validator

from .. import helpers
from .base import QCrBoxPydanticBaseModel
from .cif_entry_set import CifEntrySet
from .command_spec.command_spec import CommandSpecWithParameters, CommandSpecDiscriminatedUnion

__all__ = ["ApplicationSpec"]


class Namespace(UserDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for name in kwargs:
            setattr(self, name, kwargs[name])
        self._names = sorted(kwargs.keys())

    def __dir__(self):
        return self._names


class ApplicationSpecBase(QCrBoxPydanticBaseModel):
    name: str
    slug: str
    version: str
    description: str | None = None
    url: str | None = None
    email: str | None = None
    doi: str | None = None

    _cmds_by_name: Namespace = PrivateAttr

    @property
    def non_interactive_commands(self) -> list[CommandSpecDiscriminatedUnion]:
        return [cmd for cmd in self.commands if not cmd.is_interactive]

    @property
    def interactive_commands(self) -> list[CommandSpecDiscriminatedUnion]:
        return [cmd for cmd in self.commands if cmd.is_interactive]

    @property
    def cmds_by_name(self):
        return self._cmds_by_name

    @model_validator(mode="after")
    def populate_cmds_by_name(self) -> Self:
        data = {cmd.name: cmd for cmd in self.commands}
        self._cmds_by_name = Namespace(**data)
        return self

    @property
    def command_names(self) -> list[str]:
        return list(self.cmds_by_name.keys())

    def get_command_by_name(self, cmd_name: str) -> CommandSpecDiscriminatedUnion:
        return self.cmds_by_name[cmd_name]


class ApplicationSpec(ApplicationSpecBase):
    # model_config = ConfigDict(arbitrary_types_allowed=True)

    qcrbox_yaml_spec_version: str
    commands: list[CommandSpecDiscriminatedUnion] = []
    cif_entry_sets: list[CifEntrySet] = []

    @classmethod
    def from_yaml_file(cls, file_path: str | Path):
        file_path = Path(file_path)
        sys.path.insert(0, file_path.parent.absolute())
        yaml_data = yaml.safe_load(file_path.open())
        return cls(**yaml_data)

    @property
    def interactive_commands(self) -> list[CommandSpecDiscriminatedUnion]:
        return [cmd for cmd in self.commands if cmd.is_interactive]

    @field_validator("commands")
    @classmethod
    def verify_command_names_are_unique(
        cls, value: list[CommandSpecDiscriminatedUnion]
    ) -> list[CommandSpecDiscriminatedUnion]:
        command_names = [c.name for c in value]
        if len(command_names) != len(set(command_names)):
            raise ValueError(f"Command names must be unique, got: {command_names!r}")
        return value

    @model_validator(mode="after")
    def add_interactive_lifecycle_commands(self):
        for cmd in self.interactive_commands:
            for subcmd in cmd.interactive_lifecycle.commands:
                if subcmd.name not in self.cmds_by_name:
                    self.commands.append(subcmd)
                    self.cmds_by_name[subcmd.name] = subcmd
        return self

    @property
    def nats_key(self):
        slug_sanitized = helpers.sanitize_for_nats_subject(self.slug)
        version_sanitized = helpers.sanitize_for_nats_subject(self.version)
        return f"{slug_sanitized}.{version_sanitized}"


class ApplicationSpecWithCommands(ApplicationSpecBase):
    id: int
    registered_at: datetime
    commands: list[CommandSpecWithParameters]
    # cif_entry_sets: list[CifEntrySetRead] = []
