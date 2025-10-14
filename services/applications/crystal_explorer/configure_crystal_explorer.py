from pathlib import Path

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = Path(__file__).parent / "config_crystal_explorer.yaml"


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
