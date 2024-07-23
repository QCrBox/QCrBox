from typing import Annotated, Union

from pydantic import Field, Tag

from .builtin_parameter_types import *
from .filesystem_path_parameters import (
    FolderPathParameterSpec,
    GenericInputFileParameterSpec,
    GenericOutputFileParameterSpec,
    InputCifParameterSpec,
    OutputCifParameterSpec,
    WorkCifParameterSpec,
)

ParameterSpec = Annotated[
    Union[
        Annotated[InputCifParameterSpec, Tag("QCrBox.input_cif")],
        Annotated[GenericInputFileParameterSpec, Tag("QCrBox.input_file")],
        Annotated[OutputCifParameterSpec, Tag("QCrBox.output_cif")],
        Annotated[GenericOutputFileParameterSpec, Tag("QCrBox.output_file")],
        Annotated[WorkCifParameterSpec, Tag("QCrBox.work_cif")],
        Annotated[FolderPathParameterSpec, Tag("QCrBox.folder_path")],
        #
        Annotated[StrParameterSpec, Tag("str")],
        Annotated[IntParameterSpec, Tag("int")],
        Annotated[FloatParameterSpec, Tag("float")],
        Annotated[BoolParameterSpec, Tag("bool")],
    ],
    Field(discriminator="dtype"),
]
