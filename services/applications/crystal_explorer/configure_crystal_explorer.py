from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_crystal_explorer.yaml"


def prepare__interactive(input_cif_path, work_cif_path):
    input_cif_path = Path(input_cif_path)
    work_cif_path = Path(work_cif_path)

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "interactive", "input_cif_path")


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
