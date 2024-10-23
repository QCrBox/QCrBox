from pydantic import BaseModel


class QCrBoxDataFile(BaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str
    contents: bytes

    def to_response_model(self) -> "QCrBoxDataFileResponse":
        return QCrBoxDataFileResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            filename=self.filename,
            filetype=self.filetype,
        )


class QCrBoxDataFileResponse(BaseModel):
    qcrbox_file_id: str
    filename: str
    filetype: str


class QCrBoxDataset(BaseModel):
    dataset_id: str
    data_files: list[QCrBoxDataFile]

    def to_response_model(self) -> "QCrBoxDatasetResponse":
        return QCrBoxDatasetResponse(
            dataset_id=self.dataset_id,
            data_files=[f.to_response_model() for f in self.data_files],
        )


class QCrBoxDatasetResponse(BaseModel):
    dataset_id: str
    data_files: list[QCrBoxDataFileResponse]
