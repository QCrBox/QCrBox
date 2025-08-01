from abc import ABC, abstractmethod
from pathlib import Path

import nats.js.errors

from pyqcrbox import logger
from pyqcrbox.data_management.data_file import DataFileMetadata, Dataset
from pyqcrbox.helpers import generate_data_file_id, generate_dataset_id
from pyqcrbox.sql_models.calculation import CalculationDB
from pyqcrbox.sql_models.calculation_status_event import CalculationStatusDetails
from pyqcrbox.sql_models.interactive_session_info import InteractiveSessionInfo

__all__ = ["DataFileManager"]

class DatasetNotFoundError(Exception):
    pass

class CalculationAlreadyExists(Exception):
    pass


class DataFileManager(ABC):
    @abstractmethod
    async def _delete_from_kv(self, bucket: str, key: str) -> None:
        pass

    @abstractmethod
    async def _delete_from_object_store(self, bucket: str, key: str) -> None:
        pass

    @abstractmethod
    async def _get_kv_keys(self, bucket: str) -> list[str]:
        pass

    @abstractmethod
    async def _kv_key_exists(self, bucket: str, key: str) -> bool:
        pass

    @abstractmethod
    async def _retrieve_from_kv(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def _retrieve_from_object_store(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def _store_in_kv(self, bucket: str, key: str, value: bytes) -> None:
        pass

    @abstractmethod
    async def _store_in_object_store(self, bucket: str, key: str, value: bytes) -> None:
        pass

    async def _store_dataset_info(self, metadata: Dataset) -> None:
        """Add metadata about a dataset into the data manager.

        Parameters
        ----------
        dataset_info : Dataset
            A Dataset object containing metadata about the dataset.

        """
        await self._store_in_kv("datasets", metadata.dataset_id, metadata.model_dump_json().encode())

    async def _store_file_contents(self, key: str, file_contents: bytes) -> None:
        """Add the contents of a file to the data manager.

        Parameters
        ----------
        key : str
            The key to associate with the file contents.
        file_contents : bytes
            The contents of the file, as a bytes stream.

        """
        await self._store_in_object_store("data_file_contents", key, file_contents)

    async def _store_file_metadata(self, key: str, metadata: DataFileMetadata) -> None:
        """Add metadata about a data file into the data manager.

        Parameters
        ----------
        key : str
            The key to associate with the file metadata.
        metadata : DataFileMetadata
            A DataFileMetadata object containing metadata about the data file.

        """
        await self._store_in_kv("data_file_metadata", key, metadata.model_dump_json().encode())

    async def create_dataset_from_data_file(self, data_file_id: str) -> str:
        """Create a new dataset from a data file.

        Parameters
        ----------
        data_file_id : str
            The ID of the data file to create the dataset with.

        Returns
        -------
        str
            The ID of the created dataset.

        """
        dataset_id = generate_dataset_id()
        data_files = [await self.get_file_metadata(data_file_id)]
        dataset_info = Dataset(dataset_id=dataset_id, data_files={f.filename: f for f in data_files})
        await self._store_dataset_info(dataset_info)

        return dataset_id

    async def data_file_exists(self, data_file_id: str) -> bool:
        """Check that a data file exists for the given ID.

        Parameters
        ----------
        data_file_id : str
            The ID to check for a data file.

        Returns
        -------
        bool
            If the file exists or not

        """
        return await self._kv_key_exists("data_file_metadata", data_file_id)

    async def delete_data_file(self, data_file_id: str) -> None:
        """Delete a data file from the data manager.

        Parameters
        ----------
        data_file_id : str
            The ID of the data file to delete.

        """
        logger.debug(f"TODO: check if any datasets reference this file: {data_file_id}")
        await self._delete_from_kv("data_file_metadata", data_file_id)
        await self._delete_from_object_store("data_file_contents", data_file_id)

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset and its data files from the data manager.

        Parameters
        ----------
        dataset_id : str
            The ID of the dataset to delete.

        """
        try:
            dataset_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
        except KeyError:
            logger.error(f"No dataset found for id={dataset_id!r}")
            raise
        dataset = Dataset.model_validate_json(dataset_as_bytes.decode())
        logger.info(f"Removing dataset id={dataset_id!r} and data files {list(dataset.data_files.keys())}")

        for _, file_metadata in dataset.data_files.items():
            await self.delete_data_file(file_metadata.qcrbox_file_id)
        await self._delete_from_kv("datasets", dataset_id)

    async def export_data_file(
        self, data_file_id: str, output_dir: str | Path, output_filename: str | None = None
    ) -> Path:
        """Export a data file from the NATS object store to the file system.

        Parameters
        ----------
        data_file_id : str
            The ID of the data file to export.
        output_dir : str
            The directory on the file system to export to.
        output_filename : str | None
            The file name to use, by default the file name in NATS.


        Returns
        -------
        pathlib.Path
            The file path of the exported file.

        """
        file_contents = await self._retrieve_from_object_store("data_file_contents", data_file_id)
        object_store_filename = (await self.get_file_metadata(data_file_id)).filename

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = output_filename or object_store_filename
        output_path = output_dir / output_filename

        logger.debug(f"Writing {data_file_id!r} to {output_path}")
        with output_path.open("wb") as f:
            f.write(file_contents)

        logger.info(f"Exported data file {output_filename} to {output_path.resolve()}")

        return output_path

    async def get_file_metadata(self, data_file_id: str) -> DataFileMetadata:
        """Get the metadata for a data file.

        Parameters
        ----------
        data_file_id : str
            The ID of the data file to get metadata about.

        Returns
        -------
        DataFileMetadata
            A DataFileMetadata object containing metadata about the data file.

        """
        metadata_as_bytes = await self._retrieve_from_kv("data_file_metadata", data_file_id)

        return DataFileMetadata.model_validate_json(metadata_as_bytes.decode())

    async def get_data_files(self) -> list[DataFileMetadata]:
        """Get the metadata for all the data files.

        Returns
        -------
        list[DataFileMetadata]
            A list of DataFileMetadata objects.

        """
        keys = await self._get_kv_keys("data_file_metadata")
        values = [await self.get_file_metadata(key) for key in keys]

        return values

    async def get_dataset_info(self, dataset_id: str) -> Dataset:
        """Get metadata about a dataset.

        Parameters
        ----------
        dataset_id : str
            The ID of the dataset to retrieve metadata for.

        Returns
        -------
        Dataset
            A Dataset object containing metadata about the dataset.

        """
        try:
            dataset_info_as_bytes = await self._retrieve_from_kv("datasets", dataset_id)
        except KeyError as exc:
            exc_msg = f"Dataset not found: {dataset_id!r}"
            raise DatasetNotFoundError(exc_msg) from exc

        return Dataset.model_validate_json(dataset_info_as_bytes.decode())

    async def get_datasets(self) -> list[Dataset]:
        """Get metadata for each dataset in the data manager.

        Returns
        -------
        list[Dataset]
            A list of Dataset objects.

        """
        dataset_ids = await self._get_kv_keys("datasets")

        return [
            Dataset.model_validate_json(await self._retrieve_from_kv("datasets", dataset_id))
            for dataset_id in dataset_ids
        ]

    async def get_file_contents(self, data_file_id: str) -> bytes:
        """Get the contents of a data file.

        Parameters
        ----------
        data_file_id : str
            The ID of the data file to get the contents of.

        Returns
        -------
        bytes
            The contents of the file in raw binary.

        """
        file_contents = await self._retrieve_from_object_store("data_file_contents", data_file_id)

        return file_contents

    async def get_interactive_session_info(self, session_id: str) -> InteractiveSessionInfo:
        """Get metadata about an interactive session.

        Parameters
        ----------
        session_id : str
            The ID of the interactive session.

        Returns
        -------
        InteractiveSessionInfo
            An interactiveSessionInfo containing data about the interactive session.

        """
        session_info_as_bytes = await self._retrieve_from_kv("interactive_sessions", session_id)

        return InteractiveSessionInfo.model_validate_json(session_info_as_bytes.decode())

    async def get_interactive_sessions(self) -> list[InteractiveSessionInfo]:
        """Get metadata about all interactive sessions.

        Returns
        -------
        list[InteractiveSessionInfo]
            A list of InteractiveSessionInfo containing metadata about the interactive
            sessions

        """
        keys = await self._get_kv_keys("interactive_sessions")
        values = [await self.get_interactive_session_info(key) for key in keys]

        return values

    async def import_bytes(
        self,
        file_contents: bytes,
        filename: str,
        *,
        _qcrbox_file_id: str | None = None,
    ) -> str:
        """Import a byte stream as a data file into the data manager.

        This function will add both the contents of the file, in bytes, and metadata
        associated with the file.

        Parameters
        ----------
        file_contents : bytes
            The contents of the file, in binary.
        filename : str | None
            The name of the file to store as metadata.
        _qcrbox_file_id : str
            An ID to use. If an ID is not passed, an ID will be generated.

        Returns
        -------
        str
            The ID of the data file

        """
        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()
        file_extension = Path(filename).suffix[1:]
        data_file_info = DataFileMetadata(
            qcrbox_file_id=qcrbox_file_id,
            filename=filename,
            filetype=file_extension,
        )
        await self._store_file_contents(qcrbox_file_id, file_contents)
        await self._store_file_metadata(qcrbox_file_id, data_file_info)

        return qcrbox_file_id

    async def import_local_file(self, file_path: str | Path, *, _qcrbox_file_id: str | None = None) -> str:
        """Import a data file into the data manager, from a local file system.

        This function will add both the contents of the file, in bytes, and metadata
        associated with the file. It will only work with files on a local file
        system.

        Parameters
        ----------
        file_path : str | pathlib.Path
            The file path to the file to add to the data manager.
        _qcrbox_file_id : str
            An ID to use. If an ID is not passed, an ID will be generated.

        Returns
        -------
        str
            The ID of the data file

        """
        file_path = Path(file_path)
        qcrbox_file_id = _qcrbox_file_id or generate_data_file_id()

        with file_path.open("rb") as f:
            qcrbox_file_id = await self.import_bytes(f.read(), filename=file_path.name, _qcrbox_file_id=qcrbox_file_id)

        return qcrbox_file_id

    async def store_interactive_session_info(self, session_info: InteractiveSessionInfo) -> None:
        """Add metadata about an interactive session to the data manager.

        Parameters
        ----------
        session_info : InteractiveSessionInfo
            An InteractiveSessionInfo object containing metadata about the interactive
            session.

        """
        await self._store_in_kv(
            "interactive_sessions", session_info.session_id, session_info.model_dump_json().encode()
        )

    #
    async def get_calculation_details(self, key: str) -> CalculationDB:
        """Get metadata about a calculation from the data manager.

        Parameters
        ----------
        key : str
            The key for the calculation in the data manager.

        Returns
        -------
        CalculationNatsDB
            A CalculationNatsDB object containing metadata about the calculation.

        """
        calc_as_bytes = await self._retrieve_from_kv("calculations", key)
        calculation = CalculationDB.model_validate_json(calc_as_bytes.decode())

        return calculation

    #
    async def get_calculations(self) -> list[CalculationDB]:
        """Get metadata about all the calculations in the data manager.

        Returns
        -------
        list[CalculationNatsDB]
            A list of CalculationNatsDB which contain metadata about a calculation.

        """
        keys = await self._get_kv_keys("calculations")
        calculations = [await self.get_calculation_details(key) for key in keys]

        return calculations

    async def update_calculation_status_events(self, status_details: CalculationStatusDetails) -> None:
        """Append a new status to the the calculation status events for a calculation.

        Parameters
        ----------
        status_details : CalculationStatusDetails
            The calculation status details to append to the calculation.

        """
        key = status_details.calculation_id

        try:
            calc_as_bytes = await self._retrieve_from_kv("calculations", key)
        except nats.js.errors.KeyNotFoundError:
            logger.error(f"Can't find calculation {key!r} to update calculation status")
            raise

        calculation = CalculationDB.model_validate_json(calc_as_bytes.decode())
        calculation.status_events.append(status_details)
        logger.debug(f"Appending status {status_details!r} to calculation {calculation!r}")
        await self._store_in_kv(
            "calculations", key, calculation.model_dump_json(exclude={"status", "output_dataset_id"}).encode()
        )

    async def add_calculation_to_nats_kv(self, calculation: CalculationDB) -> None:
        """Add a new calculation to the NATS data manager.

        Parameters
        ----------
        calculation : CalculationNats
            An object containing metadata about the new calculation.

        Raises
        ------
        KeyError
            Raised when trying to add a new calculation to an already populated
            calculation id.

        """
        logger.debug(
            f"Adding calculation {calculation.calculation_id!r} to DataFileManager: {calculation!r}",
        )
        key = calculation.calculation_id
        calculation_keys = await self._get_kv_keys("calculations")
        if key in calculation_keys:
            raise KeyError(f"Calculation {key!r} already in DataFileManager, can't create new calculation")
        await self._store_in_kv(
            "calculations", key, calculation.model_dump_json(exclude={"status", "output_dataset_id"}).encode()
        )
