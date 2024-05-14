import pydantic
import sqlmodel


class QCrBoxPydanticBaseModel(pydantic.BaseModel):
    # model_config = pydantic.ConfigDict(extra="forbid")
    pass


class QCrBoxBaseSQLModel(sqlmodel.SQLModel):
    # model_config = pydantic.ConfigDict(extra="forbid")
    pass
