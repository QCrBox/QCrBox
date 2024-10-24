from abc import ABC, abstractmethod

__all__ = ["DataFileManager"]

from pathlib import Path

from pyqcrbox.data_management.data_file import DataFileMetadata, Dataset, DatasetResponse
from pyqcrbox.helpers import generate_data_file_id, generate_dataset_id


class DataFileManager(ABC):
    @abstractmethod
    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        pass

    @abstractmethod
    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        pass

    @abstractmethod
    async def _store_in_object_store(self, bucket: str, key: str, value: bytes) -> None:
        pass

    @abstractmethod
    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        pass

    async def store_dataset_info(self, dataset_info: Dataset) -> None:
        await self._store_in_kv("datasets", dataset_info.dataset_id, dataset_info.model_dump_json().encode())

    async def get_dataset_info(self, dataset_id: str) -> DatasetResponse:
        dataset_info_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
        return Dataset.model_validate_json(dataset_info_as_bytes.decode()).to_response_model()

    async def store_file_contents(self, key: str, file_contents: bytes) -> None:
        await self._store_in_object_store("data_file_contents", key, file_contents)

    async def get_file_contents(self, data_file_id: str) -> bytes:
        return await self._retrieve_from_object_store("data_file_contents", data_file_id)

    async def store_file_metadata(self, key: str, metadata: DataFileMetadata) -> None:
        await self._store_in_kv("data_file_metadata", key, metadata.model_dump_json().encode())

    async def get_file_metadata(self, data_file_id) -> DataFileMetadata:
        value_as_bytes = await self._retrieve_from_kv("data_file_metadata", data_file_id)
        return DataFileMetadata.model_validate_json(value_as_bytes.decode())

    async def file_exists(self, data_file_id: str) -> bool:
        return await self._kv_key_exists("data_file_metadata", data_file_id)

    async def import_bytes(
        self,
        file_contents: bytes,
        *,
        filename: str | None = None,
        _qcrbox_file_id: str | None = None,
    ) -> str:
        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()
        file_extension = Path(filename).suffix[1:]
        data_file_info = DataFileMetadata(
            qcrbox_file_id=qcrbox_file_id,
            filename=filename,
            filetype=file_extension,
        )
        await self.store_file_contents(qcrbox_file_id, file_contents)
        await self.store_file_metadata(qcrbox_file_id, data_file_info)
        return qcrbox_file_id

    async def create_dataset_from_data_file(self, data_file_id: str) -> str:
        dataset_id = generate_dataset_id()
        data_files = [await self.get_file_metadata(data_file_id)]
        dataset_info = Dataset(dataset_id=dataset_id, data_files=data_files)
        await self.store_dataset_info(dataset_info)
        return dataset_id
