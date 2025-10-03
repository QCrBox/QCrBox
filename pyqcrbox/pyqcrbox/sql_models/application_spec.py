import sys
from collections import UserDict
from datetime import datetime
from pathlib import Path
from typing import Self

import yaml
from pydantic import Field, PrivateAttr, field_validator, model_validator

from pyqcrbox._version import __version__ as pyqcrbox_version

from .. import helpers
from .base import QCrBoxPydanticBaseModel
from .cif_entry_set import CifEntrySet
from .command_spec.base_command_spec import ImplementedAs
from .command_spec.command_spec import CommandSpecDiscriminatedUnion, CommandSpecWithParametersResponse

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
    """Base class for application specification.

    Attributes
    ----------
    name : str
        The name of the application.
    slug : str
        The application slug, used to invoke the application and its commands.
    version : str
        The version number of the application, used to invoke the application
        and its commands.
    pyqcrbox_version : str
        The version of pyqcrbox the application was built with.
    description : str
        A description of the application.
    url : str
        A URL to the homepage of the application, if it has one.
    email : str
        The e-mail address of the application author, ideally the person who
        bundled the application together for QCrBox.
    doi : str
        A data object identifier for the application.
    yaml_file_path : str
        The file path to the YAML file containing the application specification.
    gui_port : str
        The port used for no-VNC, required for graphical/interactive
        applications.

    """

    name: str
    slug: str
    version: str
    pyqcrbox_version: str = pyqcrbox_version
    description: str | None = None
    url: str | None = None
    email: str | None = None
    doi: str | None = None
    yaml_file_path: str | None = Field(exclude=True, default=None)
    gui_port: str | None = None

    @field_validator("yaml_file_path", mode="before")
    @classmethod
    def convert_yaml_file_path_to_str(cls, value: str | Path | None):
        if not value:
            return None
        else:
            full_path = Path(value).resolve()
            return str(full_path)

    @property
    def yaml_file_dir(self) -> Path | None:
        if self.yaml_file_path:
            return Path(self.yaml_file_path).parent
        else:
            return None


class ApplicationSpec(ApplicationSpecBase):
    """Application specification class.

    Attributes
    ----------
    qcrbox_yaml_spec_version : str
        The YAML specification version used to parse the YAML file.
    commands : list[CommandSpec]
        A list of command specifications, for commands associated with the
        application.
    cif_entry_sets : list[CifEntrySet]
        A list of CifEntrySet specifications, which links labels used in a
        parameter specification to a collection of CIF entries/rows.

    """

    qcrbox_yaml_spec_version: str
    commands: list[CommandSpecDiscriminatedUnion] = []
    cif_entry_sets: list[CifEntrySet] = []

    _cmds_by_name: Namespace = PrivateAttr  # type: ignore

    @classmethod
    def from_yaml_file(cls, file_path: str | Path):
        yaml_file_path = Path(file_path)
        yaml_file_dir = str(yaml_file_path.parent.absolute())
        sys.path.insert(0, yaml_file_dir)
        yaml_data = yaml.safe_load(yaml_file_path.open())
        return cls(**yaml_data, yaml_file_path=str(yaml_file_path))

    @property
    def non_interactive_commands(self) -> list[CommandSpecDiscriminatedUnion]:
        return [cmd for cmd in self.commands if not cmd.is_interactive]

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

    @field_validator("commands")
    @classmethod
    def verify_implemented_as_valid(
        cls, commands: list[CommandSpecDiscriminatedUnion]
    ) -> list[CommandSpecDiscriminatedUnion]:
        for command in commands:
            if (
                command.is_non_interactive
                and command.implemented_as == ImplementedAs.cli_command
                and not command.name.startswith("__")  # this is to ignore commands in the interactive lifecycle
            ):
                raise ValueError(f"Non-interactive command cannot be a {ImplementedAs.cli_command!r}")
        return commands

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

    def get_command_spec_by_name(self, cmd_name: str) -> CommandSpecDiscriminatedUnion:
        return self.cmds_by_name[cmd_name]

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


class ApplicationSpecWithCommandsResponse(ApplicationSpecBase):
    id: int
    registered_at: datetime
    commands: list[CommandSpecWithParametersResponse]
    # cif_entry_sets: list[CifEntrySetRead] = []
