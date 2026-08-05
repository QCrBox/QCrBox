"""Tests for core-service discovery used by `qcb serve` (on-demand mode)."""

import pytest

from pyqcrbox.cli.helpers import DockerProject
from pyqcrbox.cli.helpers.compose_file_config import ComposeFileConfig

EXPECTED_CORE_SERVICES = {
    "qcrbox-syslog",
    "qcrbox-nats",
    "qcrbox-reverse-proxy",
    "qcrbox-lldap",
    "qcrbox-authelia",
    "qcrbox-docker-socket-proxy",
    "qcrbox-registry",
}


@pytest.fixture(scope="module", params=["development", "prebuilt"])
def compose_config(request):
    return ComposeFileConfig.get_config(request.param)


def test_core_services_are_the_root_compose_services(compose_config):
    assert set(compose_config.core_services) == EXPECTED_CORE_SERVICES


def test_core_services_contain_no_applications_or_base_images(compose_config):
    core = set(compose_config.core_services)
    apps = set(compose_config.services_excluding_base_images) - core
    assert "olex2" in apps  # sanity: applications are discovered separately
    assert not any(name.startswith("base-") for name in core)
    assert not core & apps


def test_quality_is_the_only_always_on_application(compose_config):
    assert compose_config.always_on_services == ["qcrbox_quality"]


def test_serving_starts_core_and_selected_always_on_services(monkeypatch):
    project = DockerProject()
    calls = []
    monkeypatch.setattr(project, "run_docker_compose_command", lambda *args, **kwargs: calls.append(args))

    project.start_up_serving_services(["mopro", "qcrbox_quality"], dry_run=False)

    assert calls == [("up", "-d", *project.core_services, "qcrbox_quality")]
    assert "mopro" not in calls[0]


def test_build_streams_docker_progress(monkeypatch):
    project = DockerProject()
    calls = []
    monkeypatch.setattr(project, "run_docker_compose_command", lambda *args, **kwargs: calls.append((args, kwargs)))

    project.build_single_docker_image("nosphera2-ptb")

    assert calls == [(('build', 'nosphera2-ptb'), {'dry_run': False, 'capture_output': False})]
