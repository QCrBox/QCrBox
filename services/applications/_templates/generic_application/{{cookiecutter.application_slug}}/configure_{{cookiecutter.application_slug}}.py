from pyqcrbox.sql_models_NEW_v2 import ApplicationSpec
from pyqcrbox.registry.client import QCrBoxClient


if __name__ == "__main__":
    application_spec = ApplicationSpec.from_yaml_file("config_{{ cookiecutter.application_slug }}.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()
