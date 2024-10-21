from pydantic import BaseModel


class QCrBoxDataFile(BaseModel):
    qcrbox_file_id: str
    filename: str | None
    contents: bytes

    def to_response_model(self) -> "QCrBoxDataFileResponse":
        return QCrBoxDataFileResponse(
            qcrbox_file_id=self.qcrbox_file_id,
            filename=self.filename,
        )


class QCrBoxDataFileResponse(BaseModel):
    qcrbox_file_id: str
    filename: str | None


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
