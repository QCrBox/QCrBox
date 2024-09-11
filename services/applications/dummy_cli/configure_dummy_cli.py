from pyqcrbox.registry.client import QCrBoxClient
from pyqcrbox.sql_models import ApplicationSpec

if __name__ == "__main__":
    application_spec = ApplicationSpec.from_yaml_file("config_dummy_cli.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()
