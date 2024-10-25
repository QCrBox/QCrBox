from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = ["DataFileMetadata", "DataFileMetadataResponse"]


class DataFileMetadata(QCrBoxPydanticBaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str

    def to_response_model(self) -> "DataFileMetadataResponse":
        return DataFileMetadataResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            filename=self.filename,
            filetype=self.filetype,
        )


class DataFileMetadataResponse(QCrBoxPydanticBaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str


class Dataset(QCrBoxPydanticBaseModel):
    dataset_id: str
    data_files: list[DataFileMetadata]

    def to_response_model(self) -> "DatasetResponse":
        return DatasetResponse(
            dataset_id=self.dataset_id,
            data_files=[f.to_response_model() for f in self.data_files],
        )


class DatasetResponse(QCrBoxPydanticBaseModel):
    dataset_id: str
    data_files: list[DataFileMetadataResponse]
