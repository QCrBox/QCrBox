from pathlib import Path

import nats.js.errors

from pyqcrbox import logger
from pyqcrbox.helpers import generate_data_file_id, generate_dataset_id

from .data_file import QCrBoxDataFile, QCrBoxDataset, QCrBoxDatasetResponse


class QCrBoxDataFileManager:
    def __init__(self):
        self.datasets = {}

    async def exists(self, qcrbox_file_id: str) -> bool:
        from pyqcrbox.services import get_nats_broker

        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        try:
            await data_file_storage.get_info(qcrbox_file_id)
            return True
        except nats.js.errors.ObjectNotFoundError:
            return False

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> str:
        with open(file_path, "rb") as f:
            return await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=_qcrbox_file_id)

    async def import_bytes(
        self, file_contents: bytes, *, filename: str | None = None, _qcrbox_file_id: str | None = None
    ) -> str:
        from pyqcrbox.services import get_nats_broker

        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()
        logger.debug(f"Storing file {filename!r} in NATS object store (id={qcrbox_file_id!r})")
        logger.warning(f"TODO: Store metadata about the file, including the filename {filename!r}")

        nats_broker = await get_nats_broker()
        data_file_storage = await nats_broker.object_storage("qcrbox_data_files")
        await data_file_storage.put(qcrbox_file_id, file_contents)
        return qcrbox_file_id

    async def create_dataset_from_data_file(self, data_file_id: str) -> str:
        dataset_id = generate_dataset_id()
        self.datasets[dataset_id] = [data_file_id]
        return dataset_id

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
        self.datasets = {}

    async def exists(self, qcrbox_file_id: str) -> bool:
        return qcrbox_file_id in self.dummy_storage

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> str:
        with open(file_path, "rb") as f:
            return await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=_qcrbox_file_id)

    async def import_bytes(
        self,
        file_contents: bytes,
        *,
        filename: str | None = None,
        _qcrbox_file_id: str | None = None,
    ) -> str:
        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()
        data_file = QCrBoxDataFile(
            qcrbox_file_id=qcrbox_file_id,
            filename=filename,
            contents=file_contents,
        )
        self.dummy_storage[qcrbox_file_id] = data_file

        return qcrbox_file_id

    async def create_dataset_from_data_file(self, data_file_id: str) -> str:
        dataset_id = generate_dataset_id()
        data_files = [await self.get_data_file(data_file_id)]
        self.datasets[dataset_id] = QCrBoxDataset(dataset_id=dataset_id, data_files=data_files)
        return dataset_id

    async def get_data_files(self) -> list[QCrBoxDataFile]:
        return list(self.dummy_storage.values())

    async def get_data_file(self, data_file_id) -> QCrBoxDataFile:
        return self.dummy_storage[data_file_id]

    async def get_datasets(self) -> list[QCrBoxDataset]:
        return list(self.datasets.values())

    async def get_dataset_info(self, dataset_id: str) -> QCrBoxDatasetResponse:
        return self.datasets[dataset_id].to_response_model()

    async def get_file_contents(self, qcrbox_file_id: str) -> bytes:
        data_file = self.dummy_storage[qcrbox_file_id]
        return data_file.contents

    async def delete(self, qcrbox_file_id: str) -> None:
        _ = self.dummy_storage.pop(qcrbox_file_id, None)
