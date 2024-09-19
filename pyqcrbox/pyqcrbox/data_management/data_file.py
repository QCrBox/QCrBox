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
