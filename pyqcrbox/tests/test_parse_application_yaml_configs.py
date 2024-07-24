import pytest
from pytest_cases import parametrize

from pyqcrbox import sql_models
from pyqcrbox.cli.helpers import get_repo_root


def find_application_yaml_config_files():
    repo_root = get_repo_root(__file__)
    config_files = sorted(repo_root.joinpath("services").rglob("config_*.yaml"))
    config_files = [f for f in config_files if "_templates" not in f.parts]  # exclude cookiecutter template
    return config_files


YAML_CONFIG_FILES = find_application_yaml_config_files()


@parametrize("cfg_file", YAML_CONFIG_FILES)
@pytest.mark.xfail(reason="TODO: update ApplicationSpecCreate to the latest YAML spec format")
def test_application_yaml_config_can_be_parsed_without_errors(cfg_file):
    """
    Application config_*.yaml files can be parsed without errors.
    """
    _ = sql_models.ApplicationSpecCreate.from_yaml_file(cfg_file)
