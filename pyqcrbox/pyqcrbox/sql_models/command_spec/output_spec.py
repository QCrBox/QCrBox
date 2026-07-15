# SPDX-License-Identifier: MPL-2.0
"""Output specifications for commands.

Command outputs are declared in their own ``outputs:`` section of the
application YAML (NOT in ``parameters:``): a command produces at most one
pipeline-continuing CIF (`QCrBox.output_cif`) plus any number of typed
artifacts (text, image, html, interactive structure/graph). Output filenames
are fixed by the spec (``filename``, defaulting to ``<name>.<ext>``) and are
injected into the command's execution namespace by the client — they are not
invocation arguments.
"""

from pathlib import PurePosixPath
from typing import Annotated, Any, ClassVar, Literal, Union

from pydantic import Field, Tag, TypeAdapter, field_validator

from pyqcrbox import settings

from ..base import QCrBoxPydanticBaseModel
from ..cif_entry_set import CifEntryLiteral, OneOfCifEntrySpec

__all__ = [
    "BaseCommandOutputSpec",
    "BaseArtifactOutputSpec",
    "OutputCifSpec",
    "OutputTextSpec",
    "OutputImageSpec",
    "OutputHtmlSpec",
    "OutputInteractiveStructureSpec",
    "OutputInteractiveGraphSpec",
    "OutputSpecDiscriminatedUnion",
    "get_output_spec_from_json",
]


class BaseCommandOutputSpec(QCrBoxPydanticBaseModel):
    """Base class for a command output declaration.

    Attributes
    ----------
    name : str
        The output name/identifier. The client injects the output's filename
        under this name into the command's execution namespace (python
        callable keyword argument / CLI call-pattern placeholder).
    dtype : str
        The output data type as a string, e.g. "QCrBox.output_cif".
    description : str | None
        A human-friendly description of the output.
    filename : str | None
        The filename (relative to the calculation work directory) the command
        writes this output to. Defaults to ``<name>.<default extension>``.
    required_output : bool
        If True (the default), a missing output file fails the calculation;
        optional outputs are skipped with a log message.

    """

    _default_extension: ClassVar[str] = "dat"

    name: str = Field(max_length=settings.db.max_text_length)
    dtype: str
    description: str | None = Field(default=None, max_length=settings.db.max_desc_length)
    filename: str | None = Field(default=None, max_length=settings.db.max_text_length)
    required_output: bool = True

    @field_validator("filename")
    @classmethod
    def verify_filename_stays_in_work_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(
                f"Invalid output filename {value!r} (must be a relative path inside the work directory)"
            )
        return value

    @property
    def resolved_filename(self) -> str:
        """The filename the command is expected to write this output to."""
        return self.filename or f"{self.name}.{self._default_extension}"


class OutputCifSpec(BaseCommandOutputSpec):
    """The pipeline-continuing output CIF of a command.

    Carries the CIF entry requirements used when merging the command's output
    back into the unified input CIF.
    """

    _default_extension: ClassVar[str] = "cif"

    dtype: Literal["QCrBox.output_cif"]
    required_entries: list[CifEntryLiteral | OneOfCifEntrySpec] = []
    optional_entries: list[CifEntryLiteral | OneOfCifEntrySpec] = []
    required_entry_sets: list[str] = []
    optional_entry_sets: list[str] = []
    merge_su: bool = False
    custom_categories: list[str] = []
    invalidated_entries: list[str] = []
    output_block: int = 0  # default: select first block from output cif file

    @field_validator("required_entries", "optional_entries", mode="before")
    @classmethod
    def parse_entries(cls, v: Any) -> Any:
        if isinstance(v, list):
            return [
                OneOfCifEntrySpec(one_of=item["one_of"]) if isinstance(item, dict) and "one_of" in item else item
                for item in v
            ]
        return v


class BaseArtifactOutputSpec(BaseCommandOutputSpec):
    """Base class for typed non-CIF output artifacts (report files).

    `artifact_kind` is a class attribute matching
    `pyqcrbox.data_management.ArtifactKind` (kept as a plain string because
    sql_models must not import data_management).
    """

    artifact_kind: ClassVar[str]


class OutputTextSpec(BaseArtifactOutputSpec):
    dtype: Literal["QCrBox.output_text"]
    artifact_kind: ClassVar[str] = "text"
    _default_extension: ClassVar[str] = "txt"


class OutputImageSpec(BaseArtifactOutputSpec):
    dtype: Literal["QCrBox.output_image"]
    artifact_kind: ClassVar[str] = "image"
    _default_extension: ClassVar[str] = "png"


class OutputHtmlSpec(BaseArtifactOutputSpec):
    dtype: Literal["QCrBox.output_html"]
    artifact_kind: ClassVar[str] = "html"
    _default_extension: ClassVar[str] = "html"


class OutputInteractiveStructureSpec(BaseArtifactOutputSpec):
    dtype: Literal["QCrBox.output_interactive_structure"]
    artifact_kind: ClassVar[str] = "interactive_structure"
    _default_extension: ClassVar[str] = "cif"


class OutputInteractiveGraphSpec(BaseArtifactOutputSpec):
    dtype: Literal["QCrBox.output_interactive_graph"]
    artifact_kind: ClassVar[str] = "interactive_graph"
    _default_extension: ClassVar[str] = "json"


OutputSpecTaggedUnion = Union[  # noqa: UP007
    Annotated[OutputCifSpec, Tag("QCrBox.output_cif")],
    Annotated[OutputTextSpec, Tag("QCrBox.output_text")],
    Annotated[OutputImageSpec, Tag("QCrBox.output_image")],
    Annotated[OutputHtmlSpec, Tag("QCrBox.output_html")],
    Annotated[OutputInteractiveStructureSpec, Tag("QCrBox.output_interactive_structure")],
    Annotated[OutputInteractiveGraphSpec, Tag("QCrBox.output_interactive_graph")],
]

OutputSpecDiscriminatedUnion = Annotated[OutputSpecTaggedUnion, Field(discriminator="dtype")]
output_spec_adapter: TypeAdapter[OutputSpecTaggedUnion] = TypeAdapter(OutputSpecDiscriminatedUnion)


def get_output_spec_from_json(output_spec_json: dict) -> OutputSpecDiscriminatedUnion:
    return output_spec_adapter.validate_python(output_spec_json)
