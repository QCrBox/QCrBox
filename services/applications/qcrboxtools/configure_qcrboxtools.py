
from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_qcrboxtools.yaml"

if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
