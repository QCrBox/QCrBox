import contextlib

import nats.js.errors
from faststream.nats import NatsBroker

from .data_manager import DataManager


class NatsDataManager(DataManager):
    def __init__(self, nats_broker: NatsBroker):
        self._nats_broker = nats_broker

    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        kv = await self._nats_broker.key_value(bucket)
        try:
            await kv.get(key)
            return True
        except nats.js.errors.KeyNotFoundError:
            return False

    async def _get_kv_keys(self, bucket: str) -> list[str]:
        kv = await self._nats_broker.key_value(bucket)
        try:
            keys = await kv.keys()
            return keys
        except nats.js.errors.NoKeysError:
            return []

    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        kv = await self._nats_broker.key_value(bucket)
        await kv.put(key, value)

    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        kv = await self._nats_broker.key_value(bucket)
        try:
            item = await kv.get(key)
        except nats.js.errors.KeyNotFoundError as exc:
            raise KeyError(f"Key not found: {key}") from exc
        if item.value is None:
            raise ValueError(f"Value for key '{key}' is None")
        return item.value

    async def _delete_from_kv(self, bucket: str, key: str) -> None:
        kv = await self._nats_broker.key_value(bucket)
        await kv.delete(key)

    async def _store_in_object_store(self, bucket: str, key: str, value: bytes) -> None:
        object_store = await self._nats_broker.object_storage(bucket)
        await object_store.put(key, value)

    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        object_store = await self._nats_broker.object_storage(bucket)
        obj = await object_store.get(key)
        if obj.data is None:
            raise ValueError(f"Data for key '{key}' is None")
        return obj.data

    async def _delete_from_object_store(self, bucket: str, key: str) -> None:
        object_store = await self._nats_broker.object_storage(bucket)
        with contextlib.suppress(nats.js.errors.ObjectNotFoundError):
            await object_store.delete(key)
