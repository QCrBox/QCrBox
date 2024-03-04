from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class CifEntryBase(QCrBoxPydanticBaseModel):
    name: str
    required: Optional[bool] = True


class CifEntryDB(CifEntryBase, QCrBoxBaseSQLModel, table=True):
    # __table_args__ = (UniqueConstraint("name", "cif_entry_set_id"), {"extend_existing": True})
    __tablename__ = "cif_entry"
    __table_args__ = (UniqueConstraint("name"), {"extend_existing": True})

    id: Optional[int] = Field(default=None, primary_key=True)

    cif_entry_set_id: Optional[int] = Field(default=None, foreign_key="cif_entry_set.id")
    cif_entry_set: "CifEntrySetDB" = Relationship(back_populates="cif_entries")


class CifEntryCreate(CifEntryBase):
    __qcrbox_sql_model__ = CifEntryDB


class CifEntrySimple(QCrBoxPydanticBaseModel):
    __qcrbox_sql_model__ = CifEntryDB

    name: str

    def to_cif_entry_create(self, required: bool):
        return CifEntryCreate(name=self.name, required=required)
