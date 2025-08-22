from pyqcrbox.data_management.data_file import DataFile, DataFileResponse
from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = [
    "Dataset",
    "DatasetResponse",
]


class Dataset(QCrBoxPydanticBaseModel):
    """Metadata for a dataset in the DataManager.

    Attributes
    ----------
    dataset_id : str
        Unique identifier for the dataset.
    data_files : dict[str, DataFile]
        Dictionary of data files in the dataset, keyed by filename.

    """

    dataset_id: str
    data_files: dict[str, DataFile]

    @property
    def is_empty(self):
        """Check if the dataset contains no data files.

        Returns
        -------
        bool
            True if the dataset is empty, False otherwise.

        """
        return len(self.data_files) == 0

    @property
    def contains_single_file(self):
        """Check if the dataset contains exactly one data file.

        Returns
        -------
        bool
            True if the dataset contains one file, False otherwise.

        """
        return len(self.data_files) == 1

    @property
    def contains_multiple_files(self):
        """Check if the dataset contains more than one data file.

        Returns
        -------
        bool
            True if the dataset contains multiple files, False otherwise.

        """
        return len(self.data_files) > 1

    @property
    def first_data_file(self) -> DataFile:
        """Get the first data file in the dataset.

        Returns
        -------
        DataFile
            The first DataFile in the dataset.

        """
        return next(iter(self.data_files.values()))

    def to_response_model(self) -> "DatasetResponse":
        """Convert to a DatasetResponse for API responses.

        Returns
        -------
        DatasetResponse
            The response model representation of this dataset.

        """
        return DatasetResponse(
            qcrbox_dataset_id=self.dataset_id,
            data_files={key: f.to_response_model() for key, f in self.data_files.items()},
        )


class DatasetResponse(QCrBoxPydanticBaseModel):
    """Response model for a dataset, used in API responses.

    Attributes
    ----------
    qcrbox_dataset_id : str
        Unique identifier for the dataset.
    data_files : dict[str, DataFileResponse]
        Dictionary of data files in the dataset, keyed by filename.

    """

    qcrbox_dataset_id: str
    data_files: dict[str, DataFileResponse]
