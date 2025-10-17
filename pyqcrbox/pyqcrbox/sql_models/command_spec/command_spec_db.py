from typing import TYPE_CHECKING, Any

from sqlmodel import JSON, Field, Relationship, UniqueConstraint

from pyqcrbox import settings

from ..base import QCrBoxBaseSQLModel
from .base_command_spec import ImplementedAs
from .command_spec import CommandSpec

if TYPE_CHECKING:
    from pyqcrbox.sql_models import ApplicationSpecDB, CommandSpecWithParametersResponse


class CommandSpecDB(QCrBoxBaseSQLModel, table=True):
    """Model for storing command specifications associated with an application."""

    __tablename__ = "command"
    __table_args__ = (UniqueConstraint("name", "application_id"),)
    __pydantic_model_cls__ = CommandSpec

    name: str = Field(max_length=settings.db.max_text_length)
    description: str | None = Field(default=None, max_length=settings.db.max_desc_length)
    merge_cif_su: bool = False
    implemented_as: ImplementedAs
    doi: str | None = None

    # for CLI commands
    call_pattern: str | None = None
    parameters: dict[Any, Any] = Field(sa_type=JSON)

    # for Python callables
    import_path: str | None = None
    callable_name: str | None = None

    id: int | None = Field(default=None, primary_key=True)

    application_id: int | None = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="commands")

    def model_dump(self, as_response_model: bool = False, **kwargs: dict[str, Any]) -> dict:
        """Serialise the CommandSpecDB model to a dictionary representation.

        Parameters
        ----------
        as_response_model : bool, optional
            If True, excludes certain fields that should not be returned in API responses.
        **kwargs : dict, optional
            Additional keyword arguments passed to the parent class's `model_dump` method.

        Returns
        -------
        dict
            The serialised representation of the CommandSpecDB model.

        Raises
        ------
        ValueError
            If `exclude` is provided in kwargs when `as_response_model` is True.

        """
        if as_response_model:
            if "exclude" in kwargs:
                exc_msg = "Cannot use `exclude` with mode as_response_model=True"
                raise ValueError(exc_msg)
            kwargs["exclude"] = ["call_pattern", "callable_name", "import_path"]
        else:
            kwargs.setdefault("exclude", [])

        data = super().model_dump(**kwargs)
        data["implemented_as"] = (  # before this is committed to the database, this is an enum instead of an str
            self.implemented_as.value if isinstance(self.implemented_as, ImplementedAs) else self.implemented_as
        )

        if "application" not in kwargs["exclude"]:
            data["application"] = self.application.slug
        if "cmd_name" not in kwargs["exclude"]:
            data["cmd_name"] = data["name"]  # alias

        # Kludge for how CommandSpecDB handles making response models for API requests.
        # For some reason this model_dump method has a as_response_model flag
        if as_response_model and "version" not in kwargs["exclude"]:
            data["version"] = self.application.version

        return data

    @classmethod
    def from_pydantic_model(cls, command: CommandSpec) -> "CommandSpecDB":
        """Create a CommandSpecDB instance from a Pydantic model.

        Parameters
        ----------
        command : CommandSpec
            An instance of a CommandSpec Pydantic model to convert into a CommandSpecDB
            instance.

        Returns
        -------
        CommandSpecDB
            A new CommandSpecDB instance

        """
        data = command.model_dump(exclude={"parameters"})
        data["parameters"] = {param.name: param.model_dump() for param in command.parameters}

        return cls(**data)

    def to_response_model(self) -> "CommandSpecWithParametersResponse":
        """Convert this instance into a response model for API responses.

        Returns
        -------
        CommandSpecWithParameters
            The response model

        """
        from .command_spec import CommandSpecWithParametersResponse

        data = self.model_dump(as_response_model=True)

        return CommandSpecWithParametersResponse(**data)
