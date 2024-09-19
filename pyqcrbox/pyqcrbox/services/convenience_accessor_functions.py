import svcs

from pyqcrbox.data_management import QCrBoxDataFileManager
from pyqcrbox.services.services_registry import QCRBOX_GLOBAL_SERVICES_REGISTRY


def get_data_file_manager():
    with svcs.Container(QCRBOX_GLOBAL_SERVICES_REGISTRY) as con:
        return con.get(QCrBoxDataFileManager)
