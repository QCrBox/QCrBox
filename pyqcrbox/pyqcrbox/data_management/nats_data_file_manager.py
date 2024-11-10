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

    async def _get_kv_keys(self, bucket: str) -> list[str]:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        try:
            keys = await kv.keys()
            return keys
        except nats.js.errors.NoKeysError:
            return []

    # async def _get_kv_values(self, bucket: str) -> list[Any]:
    #     from pyqcrbox.services import get_nats_broker
    #
    #     nats_broker = await get_nats_broker()
    #     kv = await nats_broker.key_value(bucket)
    #     try:
    #         keys = await kv.keys()
    #         values = [(await kv.get(key)).value for key in keys]
    #     except nats.js.errors.NoKeysError:
    #         values = []
    #
    #     return values

    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        await kv.put(key, value)

    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        try:
            item = await kv.get(key)
        except nats.js.errors.KeyNotFoundError:
            raise KeyError(f"Key not found: {key}")
        return item.value

    async def _delete_from_kv(self, bucket: str, key: str) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        kv = await nats_broker.key_value(bucket)
        await kv.delete(key)

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

    async def _delete_from_object_store(self, bucket: str, key: str) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        object_store = await nats_broker.object_storage(bucket)
        try:
            await object_store.delete(key)
        except nats.js.errors.ObjectNotFoundError:
            # we don't care if the object doesn't exist, only that was deleted successfully
            pass
