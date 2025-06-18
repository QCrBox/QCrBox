import typing
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, Session, SQLModel, select

from pyqcrbox.logging import logger
from pyqcrbox.settings import settings

from .application_spec import ApplicationSpec, ApplicationSpecBase
from .command_spec import CommandSpecDB

if typing.TYPE_CHECKING:
    from .application_spec import ApplicationSpecWithCommands


class ApplicationSpecDB(ApplicationSpecBase, SQLModel, table=True):
    """Model for storing application specifications."""

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

    def merge_commands(self, current_app: "ApplicationSpecDB", session: Session) -> None:
        """Synchronise commands of this instance with a database entry.

        This performs an in-place merge update:
        - Updates existing CommandSpecDB entries in the database which match by
          name.
        - Adds new commands found in this instance but missing in the database.
        - Removes any commands in the database which are not present in this instance.

        Parameters
        ----------
        current_app : ApplicationSpecDB
            The existing application instance from the database.
        session : Session
            The SQLModel database session.

        """
        existing_cmds_by_name = {cmd.name: cmd for cmd in current_app.commands}

        for new_cmd in self.commands:
            # Update fields on existing command OR create and append a new command
            # entry
            if new_cmd.name in existing_cmds_by_name:
                existing_cmd = existing_cmds_by_name[new_cmd.name]
                updates = new_cmd.model_dump(exclude={"id", "application", "application_id"})
                for key, value in updates.items():
                    setattr(existing_cmd, key, value)
            else:
                cmd_copy = CommandSpecDB.from_pydantic_model(new_cmd)
                cmd_copy.application_id = current_app.id
                current_app.commands.append(cmd_copy)

        # Remove commands from the database which aren't in self.commands
        new_cmd_names = {cmd.name for cmd in self.commands}
        to_remove = [cmd for cmd in current_app.commands if cmd.name not in new_cmd_names]
        for cmd in to_remove:
            session.delete(cmd)
            current_app.commands.remove(cmd)  # Not sure if I need this, but ensures consistency

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
                logger.debug(
                    f"Currently registered application: {result!r}",
                )

                excluded_fields = ["call_pattern", "callable_name", "import_path", "id", "application_id"]
                result_commands = [cmd.model_dump(exclude=excluded_fields) for cmd in result.commands]
                self_commands = [cmd.model_dump(exclude=excluded_fields) for cmd in self.commands]

                if self_commands != result_commands:
                    logger.warning(
                        "The previously registered application does not have the same commands as the current "
                        "application specification. The registered application will be updated to match the "
                        "latest application specification.",
                    )
                    self.merge_commands(result, session)

                    session.commit()
                    session.refresh(result)
                    logger.debug(
                        f"Newly registered application: {result}",
                    )

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
