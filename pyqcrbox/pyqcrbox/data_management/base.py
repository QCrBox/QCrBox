from abc import ABC, abstractmethod

__all__ = ["DataFileManager"]

from typing import assert_never

from pyqcrbox.sql_models import QCrBoxPydanticBaseModel


class DataFileManager(ABC):
    @abstractmethod
    async def _store_in_kv(self, bucket: str, key: str, value: QCrBoxPydanticBaseModel):
        assert_never(bucket)

    @abstractmethod
    async def _retrieve_from_kv(
        self, bucket: str, key: str, value_cls: QCrBoxPydanticBaseModel
    ) -> QCrBoxPydanticBaseModel:
        assert_never(bucket)
