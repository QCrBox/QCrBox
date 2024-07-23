import sys

import importlib.util
from pathlib import Path

import yaml
from pydantic import field_validator

from .base import QCrBoxPydanticBaseModel
from .cif_entry_set import CifEntrySet
from .command import CommandSpec

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

        # Dynamically import the
        #module_name = file_path.stem
        module_file_path = file_path.parent / "configure_olex2.py"
        module_name = module_file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, module_file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return cls(**yaml.safe_load(file_path.open()))
