from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = [
    "DataFile",
    "DataFileResponse",
]


class DataFile(QCrBoxPydanticBaseModel):
    """Metadata for a data file in the DataManager.

    Attributes
    ----------
    qcrbox_file_id : str
        Unique identifier for the data file.
    qcrbox_dataset_id : str | None
        Identifier for the dataset this data file is in. If None, the data file
        is not in a dataset.
    filename : str
        Name of the file.
    filetype : str
        File extension/type (e.g., 'csv', 'txt').
    kind : str | None
        Artifact kind for typed command output artifacts (see
        `pyqcrbox.data_management.ArtifactKind`). None for pipeline CIFs and
        plain uploads.

    """

    qcrbox_file_id: str
    qcrbox_dataset_id: str | None
    filename: str
    filetype: str
    kind: str | None = None

    def to_response_model(self) -> "DataFileResponse":
        """Convert to a DataFileResponse for API responses.

        Returns
        -------
        DataFileResponse
            The response model representation of this data file.

        """
        return DataFileResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            qcrbox_dataset_id=self.qcrbox_dataset_id,
            filename=self.filename,
            filetype=self.filetype,
            kind=self.kind,
        )


class DataFileResponse(QCrBoxPydanticBaseModel):
    """Response model for a data file, used in API responses.

    Attributes
    ----------
    qcrbox_file_id : str
        Unique identifier for the data file.
    qcrbox_dataset_id : str | None
        Identifier for the dataset this data file is in. If None, the data file
        is not in a dataset.
    filename : str
        Name of the file.
    filetype : str
        File extension/type (e.g., 'csv', 'txt').
    kind : str | None
        Artifact kind for typed command output artifacts; None for pipeline
        CIFs and plain uploads.

    """

    qcrbox_file_id: str
    qcrbox_dataset_id: str | None
    filename: str
    filetype: str
    kind: str | None = None
