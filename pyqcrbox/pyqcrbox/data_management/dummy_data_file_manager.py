from collections import defaultdict

from .base import DataFileManager


class DummyDataFileManager(DataFileManager):
    def __init__(self):
        self.dummy_storage = defaultdict(dict)
        self.datasets = {}

    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        return bucket in self.dummy_storage and key in self.dummy_storage[bucket]

    async def _store_in_kv(self, bucket: str, key: str, value: bytes):
        self.dummy_storage[bucket][key] = value

    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        return self.dummy_storage[bucket][key]

    async def _store_in_object_store(self, bucket: str, key: str, value: bytes):
        self.dummy_storage[bucket][key] = value

    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        return self.dummy_storage[bucket][key]

    # async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> str:
    #     with open(file_path, "rb") as f:
    #         return await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=_qcrbox_file_id)

    # async def get_datasets(self) -> list[QCrBoxDataset]:
    #     return list(self.datasets.values())

    # async def delete(self, qcrbox_file_id: str) -> None:
    #     _ = self.dummy_storage.pop(qcrbox_file_id, None)
