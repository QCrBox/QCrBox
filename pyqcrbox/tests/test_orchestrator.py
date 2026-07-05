"""Tests for the Docker container orchestrator (no docker daemon required)."""

import asyncio

import pytest

from pyqcrbox import sql_models
from pyqcrbox.services.orchestrator import (
    ApplicationNotRegisteredError,
    DockerOrchestrator,
    SpawnNotPossibleError,
    SpawnQuotaExceededError,
    SpawnTimeoutError,
)
from pyqcrbox.services.persistence import SQLitePersistenceAdapter
from pyqcrbox.settings import OrchestratorSettings

from .test_application_registration_api import DUMMY_CLI_SPEC_FILE

DUMMY_GUI_SPEC_FILE = DUMMY_CLI_SPEC_FILE.parent.parent / "dummy_gui" / "config_dummy_gui.yaml"
DUMMY_IMAGE = "qcrbox/dummy_cli:latest"
DUMMY_GUI_IMAGE = "qcrbox/dummy_gui:latest"


class FakeContainer:
    def __init__(self, container_id: str):
        self.id = container_id
        self.started = False
        self.deleted = False

    async def start(self):
        self.started = True

    async def delete(self, force=False):
        self.deleted = True


class FakeDocker:
    def __init__(self):
        self.create_calls: list[tuple[dict, str]] = []
        self.containers_by_id: dict[str, FakeContainer] = {}
        self.closed = False
        self.containers = self

    async def create(self, config: dict, name: str) -> FakeContainer:
        self.create_calls.append((config, name))
        container = FakeContainer(f"fakecontainer{len(self.create_calls):04d}" + "0" * 52)
        self.containers_by_id[container.id] = container
        return container

    async def list(self, all=False, filters=None):
        return []

    def container(self, container_id: str) -> FakeContainer:
        return self.containers_by_id[container_id]

    async def close(self):
        self.closed = True


def make_orchestrator(fake_docker: FakeDocker, **settings_overrides) -> DockerOrchestrator:
    settings_kwargs = {
        "enabled": True,
        "network_name": "test-qcrbox-net",
        "spawn_timeout": 5.0,
        "poll_interval": 0.02,
        **settings_overrides,
    }
    orchestrator_settings = OrchestratorSettings(**settings_kwargs)
    return DockerOrchestrator(orchestrator_settings=orchestrator_settings, docker_factory=lambda: fake_docker)


@pytest.fixture
def adapter() -> SQLitePersistenceAdapter:
    return SQLitePersistenceAdapter()


@pytest.fixture
async def registered_application(clean_registry_db, adapter) -> sql_models.ApplicationSpecDB:
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    spec.docker_image = DUMMY_IMAGE
    return await adapter.save_application_spec(spec)


async def simulate_client_registration(adapter, fake_docker: FakeDocker, application_id: int):
    """Wait for the orchestrator to create a container, then register 'its' client."""
    while not fake_docker.create_calls:
        await asyncio.sleep(0.01)
    config, _name = fake_docker.create_calls[-1]
    client_id = next(e.split("=", 1)[1] for e in config["Env"] if e.startswith("QCRBOX_CLIENT_ID="))
    await adapter.save_container_instance(
        application_id=application_id,
        client_id=client_id,
        private_inbox=f"_INBOX.spawned.{client_id[-8:]}",
        pyqcrbox_version="test-version",
    )
    return client_id


@pytest.mark.anyio
async def test_spawn_creates_container_with_expected_config(adapter, registered_application):
    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker)

    registration_task = asyncio.create_task(
        simulate_client_registration(adapter, fake_docker, registered_application.id)
    )
    instance = await orchestrator.ensure_instance("dummy_cli", "0.1.0")
    client_id = await registration_task

    assert instance.client_id == client_id
    config, name = fake_docker.create_calls[0]
    assert config["Image"] == DUMMY_IMAGE
    assert f"QCRBOX_CLIENT_ID={client_id}" in config["Env"]
    assert "QCRBOX__NATS__HOST=qcrbox-nats" in config["Env"]
    assert config["Labels"]["org.qcrbox.spawned"] == "true"
    assert config["Labels"]["org.qcrbox.application_slug"] == "dummy_cli"
    assert config["HostConfig"]["NetworkMode"] == "test-qcrbox-net"
    assert config["HostConfig"]["RestartPolicy"] == {"Name": "unless-stopped"}
    assert "Binds" not in config["HostConfig"]
    assert name.startswith("qcrbox-spawned-dummy_cli-")
    # Non-GUI applications get no Traefik route
    assert not any(key.startswith("traefik.") for key in config["Labels"])

    # The docker container id is persisted on the instance row
    stored = await adapter.get_instance_by_client_id(client_id)
    assert stored.docker_container_id is not None
    assert stored.docker_container_id.startswith("fakecontainer")


@pytest.mark.anyio
async def test_ensure_instance_reuses_existing_live_instance(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0xexisting",
        private_inbox="_INBOX.existing.1",
        pyqcrbox_version="test-version",
    )
    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker)

    instance = await orchestrator.ensure_instance("dummy_cli", "0.1.0")
    assert instance.client_id == "qcrbox_client_0xexisting"
    assert fake_docker.create_calls == []


@pytest.mark.anyio
async def test_spawn_times_out_and_removes_container(adapter, registered_application):
    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker, spawn_timeout=0.1)

    with pytest.raises(SpawnTimeoutError):
        await orchestrator.ensure_instance("dummy_cli", "0.1.0")

    (container,) = fake_docker.containers_by_id.values()
    assert container.started is True
    assert container.deleted is True


@pytest.mark.anyio
async def test_spawn_requires_registered_docker_image(adapter, clean_registry_db):
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    await adapter.save_application_spec(spec)  # no docker_image
    orchestrator = make_orchestrator(FakeDocker())

    with pytest.raises(SpawnNotPossibleError, match="No docker image registered"):
        await orchestrator.ensure_instance("dummy_cli", "0.1.0")
    with pytest.raises(ApplicationNotRegisteredError):
        await orchestrator.ensure_instance("no_such_app", "1.0")


@pytest.mark.anyio
async def test_spawn_instance_enforces_quota(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.q.1",
        pyqcrbox_version="test-version",
    )
    orchestrator = make_orchestrator(FakeDocker(), max_instances_per_app=1)

    with pytest.raises(SpawnQuotaExceededError):
        await orchestrator.spawn_instance("dummy_cli", "0.1.0")


@pytest.mark.anyio
async def test_concurrent_ensure_instance_spawns_only_once(adapter, registered_application):
    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker)

    registration_task = asyncio.create_task(
        simulate_client_registration(adapter, fake_docker, registered_application.id)
    )
    results = await asyncio.gather(
        orchestrator.ensure_instance("dummy_cli", "0.1.0"),
        orchestrator.ensure_instance("dummy_cli", "0.1.0"),
    )
    await registration_task

    assert len(fake_docker.create_calls) == 1
    assert results[0].client_id == results[1].client_id


@pytest.mark.anyio
async def test_gui_application_spawn_gets_traefik_route(adapter, clean_registry_db):
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_GUI_SPEC_FILE)
    spec.docker_image = DUMMY_GUI_IMAGE
    application = await adapter.save_application_spec(spec)

    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker)
    registration_task = asyncio.create_task(simulate_client_registration(adapter, fake_docker, application.id))
    instance = await orchestrator.ensure_instance("dummy_gui", "0.1.0")
    client_id = await registration_task

    config, _name = fake_docker.create_calls[0]
    suffix = client_id[-8:]
    expected_host = f"dummy-gui-{suffix}.gui.qcrbox.localhost"
    labels = config["Labels"]
    assert labels["traefik.enable"] == "true"
    assert labels[f"traefik.http.routers.qcrbox-gui-{suffix}.rule"] == f"Host(`{expected_host}`)"
    assert labels[f"traefik.http.routers.qcrbox-gui-{suffix}.entrypoints"] == "websecure"
    assert labels[f"traefik.http.routers.qcrbox-gui-{suffix}.middlewares"] == (
        f"authelia-auth,qcrbox-gui-{suffix}-redirect"
    )
    assert labels[f"traefik.http.services.qcrbox-gui-{suffix}.loadbalancer.server.port"] == "8080"
    assert expected_host in labels[f"traefik.http.middlewares.qcrbox-gui-{suffix}-redirect.redirectregex.replacement"]

    assert instance.gui_host == expected_host
    stored = await adapter.get_instance_by_client_id(client_id)
    assert stored.gui_host == expected_host


@pytest.mark.anyio
async def test_remove_instance_tolerates_already_removed_container(adapter, registered_application):
    """A stale row whose docker container no longer exists must still be deletable."""

    class Missing404(Exception):
        status = 404

    class FakeDockerMissingContainer(FakeDocker):
        def container(self, container_id: str):
            class _Gone:
                async def delete(self, force=False):
                    raise Missing404("no such container")

            return _Gone()

    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0xstale",
        private_inbox="_INBOX.stale.1",
        pyqcrbox_version="test-version",
    )
    await adapter.set_instance_spawn_details("qcrbox_client_0xstale", "deadbeef" * 8)
    instance = await adapter.get_instance_by_client_id("qcrbox_client_0xstale")

    orchestrator = make_orchestrator(FakeDockerMissingContainer())
    assert await orchestrator.remove_instance(instance.id) is True
    assert await adapter.get_instance_by_client_id("qcrbox_client_0xstale") is None


@pytest.mark.anyio
async def test_spawn_attributes_owner_on_instance_row(adapter, registered_application):
    fake_docker = FakeDocker()
    orchestrator = make_orchestrator(fake_docker)
    registration_task = asyncio.create_task(
        simulate_client_registration(adapter, fake_docker, registered_application.id)
    )
    instance = await orchestrator.ensure_instance("dummy_cli", "0.1.0", owner="alice")
    client_id = await registration_task

    assert instance.owner_user_id == "alice"
    stored = await adapter.get_instance_by_client_id(client_id)
    assert stored.owner_user_id == "alice"


@pytest.mark.anyio
async def test_docker_image_upsert_never_cleared_by_null(adapter, registered_application):
    """Re-registration without an image (container self-registration) must keep the stored image."""
    spec_without_image = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    saved = await adapter.save_application_spec(spec_without_image)
    assert saved.docker_image == DUMMY_IMAGE

    spec_with_new_image = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    spec_with_new_image.docker_image = "qcrbox/dummy_cli:new-tag"
    saved = await adapter.save_application_spec(spec_with_new_image)
    assert saved.docker_image == "qcrbox/dummy_cli:new-tag"
