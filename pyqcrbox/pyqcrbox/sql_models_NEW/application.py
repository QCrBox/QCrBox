from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

from .cif_entry_set import CifEntrySetCreate
from .command import CommandSpecCreate

__all__ = ["ApplicationSpecCreate"]


class ApplicationSpecBase(BaseModel):
    name: str
    slug: str
    version: str
    description: str | None = None
    url: str | None = None
    email: str | None = None


class ApplicationSpecCreate(ApplicationSpecBase):
    commands: list[CommandSpecCreate] = []
    cif_entry_sets: list[CifEntrySetCreate] = []

    @field_validator("commands")
    @classmethod
    def verify_command_names_are_unique(cls, value: list[CommandSpecCreate]) -> list[CommandSpecCreate]:
        command_names = [c.name for c in value]
        if len(command_names) != len(set(command_names)):
            raise ValueError("Command names must be unique")
        return value

    @classmethod
    def from_yaml_file(cls, path: str | Path):
        return cls(**yaml.safe_load(Path(path).open()))
