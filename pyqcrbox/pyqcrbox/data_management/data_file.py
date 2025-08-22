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
    filename : str
        Name of the file.
    filetype : str
        File extension/type (e.g., 'csv', 'txt').

    """

    qcrbox_file_id: str
    filename: str
    filetype: str

    def to_response_model(self) -> "DataFileResponse":
        """Convert to a DataFileResponse for API responses.

        Returns
        -------
        DataFileResponse
            The response model representation of this data file.

        """
        return DataFileResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            filename=self.filename,
            filetype=self.filetype,
        )


class DataFileResponse(QCrBoxPydanticBaseModel):
    """Response model for a data file, used in API responses.

    Attributes
    ----------
    qcrbox_file_id : str
        Unique identifier for the data file.
    filename : str
        Name of the file.
    filetype : str
        File extension/type (e.g., 'csv', 'txt').

    """

    qcrbox_file_id: str
    filename: str
    filetype: str
