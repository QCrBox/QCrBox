"""Tests for core-service discovery used by `qcb serve` (on-demand mode)."""

import pytest

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
