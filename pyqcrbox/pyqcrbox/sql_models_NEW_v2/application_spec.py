from pathlib import Path

import yaml
from pydantic import field_validator

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
