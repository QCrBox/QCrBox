from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = ["DataFileMetadata", "DataFileInfoResponse", "Dataset", "DatasetInfoResponse"]


class DataFileMetadata(QCrBoxPydanticBaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str

    def to_response_model(self) -> "DataFileInfoResponse":
        return DataFileInfoResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            filename=self.filename,
            filetype=self.filetype,
        )


class DataFileInfoResponse(QCrBoxPydanticBaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str


class DatasetBase(QCrBoxPydanticBaseModel):
    @property
    def is_empty(self):
        return len(self.data_files) == 0

    @property
    def contains_single_file(self):
        return len(self.data_files) == 1

    @property
    def contains_multiple_files(self):
        return len(self.data_files) > 1

    @property
    def first_data_file(self) -> DataFileMetadata:
        return next(iter(self.data_files.values()))


class Dataset(DatasetBase):
    dataset_id: str
    data_files: dict[str, DataFileMetadata]

    def to_response_model(self) -> "DatasetInfoResponse":
        return DatasetInfoResponse(
            qcrbox_dataset_id=self.dataset_id,
            data_files={key: f.to_response_model() for key, f in self.data_files.items()},
        )


class DatasetInfoResponse(DatasetBase):
    qcrbox_dataset_id: str
    data_files: dict[str, DataFileInfoResponse]
