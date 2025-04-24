from abc import ABC, abstractmethod

__all__ = ["DataFileManager"]

from pathlib import Path

from pyqcrbox import logger
from pyqcrbox.data_management.data_file import DataFileMetadata, Dataset, DatasetResponse
from pyqcrbox.helpers import generate_data_file_id, generate_dataset_id
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfo


class DatasetNotFoundError(Exception):
    pass


class DataFileManager(ABC):
    @abstractmethod
    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        pass

    @abstractmethod
    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        pass

    @abstractmethod
    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def _delete_from_kv(self, bucket: str, key: str) -> None:
        pass

    @abstractmethod
    async def _get_kv_keys(self, bucket: str) -> list[str]:
        pass

    @abstractmethod
    async def _store_in_object_store(self, bucket: str, key: str, value: bytes) -> None:
        pass

    @abstractmethod
    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def _delete_from_object_store(self, bucket: str, key: str) -> None:
        pass

    async def store_interactive_session_info(self, session_info: InteractiveSessionInfo) -> None:
        await self._store_in_kv(
            "interactive_sessions", session_info.session_id, session_info.model_dump_json().encode()
        )

    async def get_interactive_session_info(self, session_id: str) -> InteractiveSessionInfo:
        session_info_as_bytes = await self._retrieve_from_kv("interactive_sessions", session_id)
        return InteractiveSessionInfo.model_validate_json(session_info_as_bytes.decode())

    async def get_datasets(self) -> list[Dataset]:
        datasets = []
        for dataset_id in await self._get_kv_keys("datasets"):
            try:
                dataset_info_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
            except KeyError:
                logger.warning(f"Dataset not found: {dataset_id!r}")
                continue
            dataset = Dataset.model_validate_json(dataset_info_as_bytes.decode())
            datasets.append(dataset)

        return datasets

    async def store_dataset_info(self, dataset_info: Dataset) -> None:
        await self._store_in_kv("datasets", dataset_info.dataset_id, dataset_info.model_dump_json().encode())

    async def get_dataset_info(self, dataset_id: str) -> DatasetResponse:
        try:
            dataset_info_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
        except KeyError:
            raise DatasetNotFoundError(f"Dataset not found: {dataset_id!r}")
        return Dataset.model_validate_json(dataset_info_as_bytes.decode()).to_response_model()

    async def get_data_files_metadata(self) -> list[DataFileMetadata]:
        keys = await self._get_kv_keys("data_file_metadata")
        values = [await self.get_file_metadata(key) for key in keys]
        return values

    async def store_file_contents(self, key: str, file_contents: bytes) -> None:
        await self._store_in_object_store("data_file_contents", key, file_contents)

    async def get_file_contents(self, data_file_id: str) -> bytes:
        return await self._retrieve_from_object_store("data_file_contents", data_file_id)

    async def export_data_file(self, data_file_id: str, output_dir: str, output_filename: str | None = None) -> Path:
        file_contents = await self._retrieve_from_object_store("data_file_contents", data_file_id)
        object_store_filename = (await self.get_file_metadata(data_file_id)).filename

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filename = output_filename or object_store_filename
        output_path = output_dir / output_filename
        with output_path.open("wb") as f:
            f.write(file_contents)

        return output_path

    async def store_file_metadata(self, key: str, metadata: DataFileMetadata) -> None:
        await self._store_in_kv("data_file_metadata", key, metadata.model_dump_json().encode())

    async def get_file_metadata(self, data_file_id) -> DataFileMetadata:
        value_as_bytes = await self._retrieve_from_kv("data_file_metadata", data_file_id)
        return DataFileMetadata.model_validate_json(value_as_bytes.decode())

    async def data_file_exists(self, data_file_id: str) -> bool:
        return await self._kv_key_exists("data_file_metadata", data_file_id)

    async def delete_data_file(self, data_file_id: str) -> None:
        logger.debug(f"TODO: check if any datasets reference this file: {data_file_id}")
        await self._delete_from_kv("data_file_metadata", data_file_id)
        await self._delete_from_object_store("data_file_contents", data_file_id)

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

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id: str | None = None) -> str:
        file_path = Path(file_path)
        with file_path.open("rb") as f:
            return await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=_qcrbox_file_id)

    async def create_dataset_from_data_file(self, data_file_id: str) -> str:
        dataset_id = generate_dataset_id()
        data_files = [await self.get_file_metadata(data_file_id)]
        dataset_info = Dataset(dataset_id=dataset_id, data_files={f.filename: f for f in data_files})
        await self.store_dataset_info(dataset_info)
        return dataset_id

    async def delete_dataset(self, dataset_id: str) -> None:
        logger.debug(f"Removing dataset {dataset_id}")
        try:
            dataset_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
        except KeyError:
            logger.error(f"No dataset found for id: {dataset_id}")
            raise
        dataset = Dataset.model_validate_json(dataset_as_bytes.decode())

        for filename, file_metadata in dataset.data_files.items():
            await self.delete_data_file(file_metadata.qcrbox_file_id)
        await self._delete_from_kv("datasets", dataset_id)
