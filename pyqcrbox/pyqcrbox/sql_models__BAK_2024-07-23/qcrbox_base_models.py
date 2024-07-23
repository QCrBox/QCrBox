import pydantic
import sqlmodel


class QCrBoxPydanticBaseModel(pydantic.BaseModel):
    # model_config = pydantic.ConfigDict(extra="forbid")
    pass


class QCrBoxBaseSQLModel(sqlmodel.SQLModel):
    # model_config = pydantic.ConfigDict(extra="forbid")
    pass


class QCrBoxDBError(IOError):
    def __init__(self, msg, *args):
        super().__init__(msg, *args)  # IOError takes no keyword arguments
        self.message = msg
