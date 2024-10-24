from pathlib import Path

import nats.js.errors
import nats.js.kv
import nats.js.object_store

from .base import DataFileManager


class NatsDataFileManager(DataFileManager):
    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        try:
            await kv.get(key)
            return True
        except nats.js.errors.KeyNotFoundError:
            return False

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> str:
        with open(file_path, "rb") as f:
            return await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=_qcrbox_file_id)

    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        await kv.put(key, value)

    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        entry = await kv.get(key)
        return entry.value

    async def _store_in_object_store(self, bucket: str, key: str, value: bytes) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        object_store = await nats_broker.object_storage(bucket)
        await object_store.put(key, value)

    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        object_store = await nats_broker.object_storage(bucket)
        obj = await object_store.get(key)
        return obj.data
