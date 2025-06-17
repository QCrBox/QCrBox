import typing
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel, select

from pyqcrbox.logging import logger
from pyqcrbox.settings import settings

from .application_spec import ApplicationSpec, ApplicationSpecBase
from .calculation import CalculationDB
from .command_spec import CommandSpecDB

if typing.TYPE_CHECKING:
    from .application_spec import ApplicationSpecWithCommands


class ApplicationSpecDB(ApplicationSpecBase, SQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (UniqueConstraint("slug", "version"),)
    __pydantic_model_cls__ = ApplicationSpec

    id: int | None = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    private_routing_key: str

    commands: list[CommandSpecDB] = Relationship(back_populates="application")

    def model_dump(self, as_response_model: bool = False, **kwargs: dict[str, typing.Any]) -> dict:
        """Serialise the model to a dictionary representation.

        Parameters
        ----------
        as_response_model : bool
            If True, excludes some fields which should not be returned as a response
            from the API.
        **kwargs
            Additional keyword arguments passed to the parent class's `model_dump`

        Returns
        -------
        dict
            The serialised representation of the model.

        """
        if as_response_model:
            assert "exclude" not in kwargs
            kwargs["exclude"] = {"private_routing_key"}

        data = super().model_dump(**kwargs)
        data["commands"] = [cmd.model_dump(as_response_model=as_response_model) for cmd in self.commands]
        return data

    @classmethod
    def from_pydantic_model(
        cls, application: __pydantic_model_cls__, private_routing_key: str = None
    ) -> "ApplicationSpecDB":
        """Create an ApplicationSpecDB instance from a Pydanatic model.

        Parameters
        ----------
        application : ApplicationSpec
            The Pydantic model instance to convert.
        private_routing_key : str, optional
            The private routing key to use for the application. If not provided,
            a default value is used.

        Returns
        -------
        ApplicationSpecDB
            A new ApplicationSpecDB instance populated with data from the Pydantic
            model.

        """
        assert isinstance(application, cls.__pydantic_model_cls__)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandSpecDB.from_pydantic_model(cmd) for cmd in application.commands]
        data["private_routing_key"] = private_routing_key or "super-secret-private-routing-key-001"

        return cls(**data)

    def save_to_db(self, init_db: bool = False) -> "ApplicationSpecDB":
        """Save this ApplicationSpecDB instance to the database.

        If an entry with the same slug, version and commands exists, the entry
        is returned. Otherwise, adds the current instance to the database. If the
        current data does not agree with what is in the database, then the database
        entry is updated to reflect the data contained within this instance.

        Parameters
        ----------
        init_db : bool, optional
            If True, initialises the database session before saving.

        Returns
        -------
        ApplicationSpecDB
            The stored ApplicationSpedDB instance (either already existing or
            newly created).

        """
        cls = self.__class__

        with settings.db.get_session(init_db=init_db) as session:
            # Using the first should be sufficient as slug and version are unique keys, so there can
            # only be one entry with the same slug and version
            result = session.exec(select(cls).where(cls.slug == self.slug, cls.version == self.version)).first()

            if result:
                logger.info(
                    f"An application was registered before with slug={self.slug!r}, version={self.version!r}. "
                    "Loading details from the previously stored data."
                )

                excluded_fields = ["call_pattern", "callable_name", "import_path", "id", "application_id"]
                result_commands = [cmd.model_dump(exclude=excluded_fields) for cmd in result.commands]
                self_commands = [cmd.model_dump(exclude=excluded_fields) for cmd in self.commands]
                logger.debug(f"Self commands   : {self_commands}")
                logger.debug(f"Result commands : {result_commands}")

                if self_commands != result_commands:
                    logger.warning(
                        "The previously registered application does not have the same commands as the current "
                        "application specification. The registered application will be updated to match the "
                        "latest application specification.",
                    )

                    # result.commands = self.commands
                    # session.commit()
                    # session.refresh(result)

                return result

            session.add(self)
            session.commit()
            session.refresh(self)
            logger.info(
                f"Registered a new application with slug={self.slug!r}, version={self.version!r}",
            )

            return self

    def to_response_model(self) -> "ApplicationSpecWithCommands":
        """Convert the ApplicationSpecDB to an ApplicationSpecWithCommands response model.

        Returns
        -------
        ApplicationSpecWithCommands
            A Pydantic response model populated with data from this instance.

        """
        from .application_spec import ApplicationSpecWithCommands

        return ApplicationSpecWithCommands(**self.model_dump(as_response_model=True))
