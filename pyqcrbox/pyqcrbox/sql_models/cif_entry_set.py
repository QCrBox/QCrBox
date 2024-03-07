from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CifEntrySetCreate(QCrBoxPydanticBaseModel):
    name: str
    required: list[str] = []
    optional: list[str] = []
