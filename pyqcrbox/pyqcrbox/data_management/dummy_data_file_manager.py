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
