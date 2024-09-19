from pathlib import Path

import nats.js.errors

from pyqcrbox import logger
from pyqcrbox.helpers import generate_data_file_id


class QCrBoxDataFileManager:
    async def exists(self, qcrbox_file_id: str) -> bool:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        try:
            await data_file_storage.get_info(qcrbox_file_id)
            return True
        except nats.js.errors.ObjectNotFoundError:
            return False

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> None:
        from pyqcrbox.services import get_nats_broker

        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()
        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        with open(file_path, "rb") as f:
            logger.debug(f"Storing file {qcrbox_file_id!r} in NATS object store")
            await data_file_storage.put(qcrbox_file_id, f)

    async def get_file_contents(self, qcrbox_file_id: str) -> bytes:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        file_obj = await data_file_storage.get(qcrbox_file_id)
        return file_obj.data

    async def delete(self, qcrbox_file_id: str) -> None:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        try:
            await data_file_storage.delete(qcrbox_file_id)
        except nats.js.errors.ObjectNotFoundError:
            # We don't care if the file doesn't exist in the first place
            pass


class DummyDataFileManager:
    def __init__(self):
        self.dummy_storage = {}

    async def exists(self, qcrbox_file_id: str) -> bool:
        return qcrbox_file_id in self.dummy_storage

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> None:
        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()

        with open(file_path, "rb") as f:
            self.dummy_storage[qcrbox_file_id] = f.read()

    async def read_file(self, qcrbox_file_id: str) -> bytes:
        return self.dummy_storage[qcrbox_file_id]

    async def delete(self, qcrbox_file_id: str) -> None:
        _ = self.dummy_storage.pop(qcrbox_file_id, None)
