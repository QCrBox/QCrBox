from pathlib import Path

from pyqcrbox.helpers import generate_data_file_id, generate_dataset_id

from .base import DataFileManager
from .data_file import QCrBoxDataFile, QCrBoxDataset, QCrBoxDatasetResponse


class DummyDataFileManager(DataFileManager):
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
        file_extension = Path(filename).suffix[1:]
        data_file = QCrBoxDataFile(
            qcrbox_file_id=qcrbox_file_id,
            filename=filename,
            filetype=file_extension,
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
