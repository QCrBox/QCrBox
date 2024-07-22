from sqlmodel import Field, JSON

from ..base import QCrBoxBaseSQLModel
from .base_command_spec import ImplementedAs
from .call_pattern import CallPattern
from ..parameter_spec import ParameterSpecDiscriminatedUnion
# from .interactive_command_spec import InteractiveLifecycleSteps, NonInteractiveCommandSpec


class CommandSpecDBNEW(QCrBoxBaseSQLModel, table=True):
    name: str
    description: str = ""
    merge_cif_su: bool = False
    implemented_as: ImplementedAs
    doi: str | None = None

    # for CLI commands
    call_pattern: str | None = None
    parameters: list[dict] = Field(sa_type=JSON)

    # for Python callables
    import_path: str | None = None
    callable_name: str | None = None

    # interactive_lifecycle: InteractiveLifecycleSteps
    # non_interactive_equivalent: NonInteractiveCommandSpec

    id: int | None = Field(primary_key=True, nullable=True)
