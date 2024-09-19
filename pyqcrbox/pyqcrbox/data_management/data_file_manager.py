from pathlib import Path


class QCrBoxDataFileManager:
    pass


class DummyDataFileManager:
    def __init__(self):
        self.dummy_storage = {}

    async def exists(self, qcrbox_file_id: str):
        return qcrbox_file_id in self.dummy_storage

    async def import_local_file(self, file_path: str | Path, _qcrbox_file_id : str | None=None):
        with open(file_path, 'rb') as f:
            self.dummy_storage[_qcrbox_file_id] = f.read()

    async def read_file(self, qcrbox_file_id: str):
        return self.dummy_storage[qcrbox_file_id]
