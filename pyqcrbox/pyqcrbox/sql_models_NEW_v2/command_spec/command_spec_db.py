from typing import TYPE_CHECKING, Any

from sqlmodel import JSON, Field, Relationship, UniqueConstraint

from ..base import QCrBoxBaseSQLModel
from .base_command_spec import ImplementedAs
from .command_spec import CommandSpec

# from .interactive_command_spec import InteractiveLifecycleSteps, NonInteractiveCommandSpec

if TYPE_CHECKING:
    from pyqcrbox.sql_models_NEW_v2 import ApplicationSpecDB, CalculationDB


class CommandSpecDB(QCrBoxBaseSQLModel, table=True):
    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"),)
    __pydantic_model_cls__ = CommandSpec

    name: str
    description: str = ""
    merge_cif_su: bool = False
    implemented_as: ImplementedAs
    doi: str | None = None

    # for CLI commands
    call_pattern: str | None = None
    parameters: dict[Any, Any] = Field(sa_type=JSON)

    # for Python callables
    import_path: str | None = None
    callable_name: str | None = None

    # interactive_lifecycle: InteractiveLifecycleSteps
    # non_interactive_equivalent: NonInteractiveCommandSpec

    id: int | None = Field(default=None, primary_key=True)

    application_id: int | None = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")

    calculations: list["CalculationDB"] = Relationship(back_populates="command")

    def model_dump(self, as_response_model=False, **kwargs):
        if as_response_model:
            assert "exclude" not in kwargs
            kwargs["exclude"] = ["call_pattern", "callable_name", "import_path"]

        return super().model_dump(**kwargs)

    @classmethod
    def from_pydantic_model(cls, command):
        # pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        # assert isinstance(command, pydantic_model_cls)
        # breakpoint()
        data = command.model_dump(exclude={"parameters"})
        # data["parameters"] = [ParameterSpecDB.from_pydantic_model(param) for param in command.parameters]
        data["parameters"] = {param.name: param.model_dump() for param in command.parameters}
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)

    def to_response_model(self):
        from .command_spec import CommandSpecWithParameters

        data = self.model_dump(as_response_model=True)
        return CommandSpecWithParameters(**data)
