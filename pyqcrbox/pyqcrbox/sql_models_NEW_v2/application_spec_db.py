from sqlmodel import Field, SQLModel


class ApplicationSpecDB(SQLModel, table=True):
    __tablename__ = "application"

    id: int | None = Field(default=None, primary_key=True)
