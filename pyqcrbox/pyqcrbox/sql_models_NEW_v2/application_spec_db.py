from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from .application_spec import ApplicationSpec, ApplicationSpecBase
from .command_spec import CommandSpecDB


class ApplicationSpecDB(ApplicationSpecBase, SQLModel, table=True):
    __tablename__ = "application"
    __pydantic_model_cls__ = ApplicationSpec

    id: int | None = Field(default=None, primary_key=True)
    registered_at: datetime = Field(default_factory=datetime.now)
    private_routing_key: str

    commands: list[CommandSpecDB] = Relationship(back_populates="application")

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data["commands"] = [cmd.model_dump(**kwargs) for cmd in self.commands]
        return data

    @classmethod
    def from_pydantic_model(cls, application: __pydantic_model_cls__, private_routing_key: str = None):
        pydantic_model_cls = getattr(cls, "__pydantic_model_cls__")
        assert isinstance(application, pydantic_model_cls)
        data = application.model_dump(exclude={"commands"})
        data["commands"] = [CommandSpecDB.from_pydantic_model(cmd) for cmd in application.commands]
        data["private_routing_key"] = private_routing_key or "super-secret-private-routing-key-001"
        # logger.debug(f"{command.name=}: {data=}")
        return cls(**data)
