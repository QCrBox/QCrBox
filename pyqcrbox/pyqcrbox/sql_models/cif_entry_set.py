from .qcrbox_base_models import QCrBoxPydanticBaseModel


class CifEntrySetCreate(QCrBoxPydanticBaseModel):
    name: str
    required: list[str | dict] = []  # TODO: validate the dict structure (see 'resolution' in config_xharpy_gpaw.yaml)
    optional: list[str | dict] = []  # TODO: validate the dict structure (see 'resolution' in config_xharpy_gpaw.yaml)
