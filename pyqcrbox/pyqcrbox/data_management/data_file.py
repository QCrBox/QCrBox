from pydantic import BaseModel


class QCrBoxDataFile(BaseModel):
    qcrbox_file_id: str
    filename: str
    contents: bytes
