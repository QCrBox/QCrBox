"""Tests for resolving application docker images from compose files."""

from pathlib import Path

import pytest

from pyqcrbox.cli.helpers import DockerProject
from pyqcrbox.cli.helpers.image_resolution import (
    interpolate_compose_value,
    resolve_docker_image_for_spec_file,
)
from pyqcrbox.cli.subcommands.register import find_spec_file_for_component

REPO_ROOT = Path(__file__).parent.parent.parent


def test_interpolate_plain_variable(monkeypatch):
    monkeypatch.setenv("MY_TEST_TAG", "1.2.3")
    assert interpolate_compose_value("qcrbox/foo:${MY_TEST_TAG}", {}) == "qcrbox/foo:1.2.3"


def test_interpolate_env_file_value_and_environ_precedence(monkeypatch):
    env_vars = {"MY_TEST_TAG": "from-file"}
    monkeypatch.delenv("MY_TEST_TAG", raising=False)
    assert interpolate_compose_value("foo:${MY_TEST_TAG}", env_vars) == "foo:from-file"
    monkeypatch.setenv("MY_TEST_TAG", "from-environ")
    assert interpolate_compose_value("foo:${MY_TEST_TAG}", env_vars) == "foo:from-environ"


def test_interpolate_default_value(monkeypatch):
    monkeypatch.delenv("MY_UNSET_VAR", raising=False)
    assert interpolate_compose_value("foo:${MY_UNSET_VAR:-fallback}", {}) == "foo:fallback"


def test_interpolate_required_variable_raises(monkeypatch):
    monkeypatch.delenv("MY_UNSET_VAR", raising=False)
    with pytest.raises(ValueError, match="MY_UNSET_VAR"):
        interpolate_compose_value("foo:${MY_UNSET_VAR:?must be set}", {})


@pytest.fixture(scope="module")
def docker_project():
    return DockerProject()


def test_resolve_image_for_dummy_cli(docker_project):
    spec_file = REPO_ROOT / "services" / "applications" / "dummy_cli" / "config_dummy_cli.yaml"
    image = resolve_docker_image_for_spec_file(docker_project, spec_file)
    assert image is not None
    assert image.startswith("qcrbox/dummy_cli:")


def test_resolve_image_for_olex2_with_historic_naming(docker_project):
    """Slug `olex2`, directory `olex2_linux`, image `qcrbox/olex2-linux` — compose is authoritative."""
    spec_file = REPO_ROOT / "services" / "applications" / "olex2_linux" / "config_olex2.yaml"
    image = resolve_docker_image_for_spec_file(docker_project, spec_file)
    assert image is not None
    assert image.startswith("qcrbox/olex2-linux:")


def test_resolve_prebuilt_image_uses_repository_and_tag(monkeypatch):
    monkeypatch.setenv("QCRBOX_DOCKER_REPO", "registry.example/qcrbox")
    monkeypatch.setenv("QCRBOX_DOCKER_TAG", "stakeholder-test")
    docker_project = DockerProject(config_name="prebuilt")
    spec_file = REPO_ROOT / "services" / "applications" / "mopro" / "config_mopro.yaml"

    assert resolve_docker_image_for_spec_file(docker_project, spec_file) == (
        "registry.example/qcrbox/mopro:stakeholder-test"
    )


def test_find_spec_for_prebuilt_component():
    docker_project = DockerProject(config_name="prebuilt")

    assert find_spec_file_for_component(docker_project, "olex2") == (
        REPO_ROOT / "services" / "applications" / "olex2_linux" / "config_olex2.yaml"
    )
    assert find_spec_file_for_component(docker_project, "qcrbox_quality") is None


def test_resolve_image_returns_none_for_unknown_directory(docker_project, tmp_path):
    spec_file = tmp_path / "config_unknown.yaml"
    spec_file.touch()
    assert resolve_docker_image_for_spec_file(docker_project, spec_file) is None
