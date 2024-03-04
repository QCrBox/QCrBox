from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from .cif_entry import CifEntryCreate, CifEntryDB, CifEntrySimple
from .qcrbox_base_models import QCrBoxBaseSQLModel, QCrBoxPydanticBaseModel


class CifEntrySetBase(QCrBoxPydanticBaseModel):
    name: str


class CifEntrySetDB(CifEntrySetBase, QCrBoxBaseSQLModel, table=True):
    __tablename__ = "cif_entry_set"
    __table_args__ = (UniqueConstraint("name", "application_id"), {"extend_existing": True})

    id: Optional[int] = Field(default=None, primary_key=True)

    application_id: Optional[int] = Field(default=None, foreign_key="application.id")
    application: "ApplicationSpecDB" = Relationship(back_populates="cif_entry_sets")
    cif_entries: list[CifEntryDB] = Relationship(back_populates="cif_entry_set")


class CifEntrySetCreateImpl(CifEntrySetBase):
    __qcrbox_sql_model__ = CifEntrySetDB

    cif_entries: list[CifEntryCreate] = []


class CifEntrySetCreate(CifEntrySetBase):
    __qcrbox_sql_model__ = CifEntrySetDB

    required: list[CifEntrySimple] = []
    optional: list[CifEntrySimple] = []

    def to_sql_model(self):
        required_cif_entries = [c.to_cif_entry_create(required=True) for c in self.required]
        optional_cif_entries = [c.to_cif_entry_create(required=False) for c in self.optional]
        all_cif_entries = required_cif_entries + optional_cif_entries
        return CifEntrySetCreateImpl(name=self.name, cif_entries=all_cif_entries).to_sql_model()
