"""Tests for the container-instance API endpoints and the auto-spawn hook (no docker/NATS required)."""

import pytest
from faststream.nats import NatsBroker
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient

from pyqcrbox import sql_models
from pyqcrbox.registry.server.api.api_endpoints import api_router
from pyqcrbox.services.orchestrator import (
    ApplicationNotRegisteredError,
    ContainerOrchestrator,
    DisabledOrchestrator,
    SpawnQuotaExceededError,
    SpawnTimeoutError,
)
from pyqcrbox.services.persistence import SQLitePersistenceAdapter

from .test_application_registration_api import DUMMY_CLI_SPEC_FILE


class InMemoryOrchestrator(ContainerOrchestrator):
    """Fake orchestrator that registers an instance row instead of spawning a container."""

    def __init__(self, failure: Exception | None = None):
        self.adapter = SQLitePersistenceAdapter()
        self.failure = failure
        self.ensure_calls: list[tuple[str, str]] = []
        self.spawn_calls: list[tuple[str, str]] = []

    async def _fake_spawn(self, application_slug: str, application_version: str) -> sql_models.ContainerInstanceDB:
        if self.failure is not None:
            raise self.failure
        application = await self.adapter.get_application(application_slug, application_version)
        if application is None:
            raise ApplicationNotRegisteredError(f"Application not registered: {application_slug!r}")
        return await self.adapter.save_container_instance(
            application_id=application.id,
            client_id="qcrbox_client_0xfake",
            private_inbox="_INBOX.fake.1",
            pyqcrbox_version="test-version",
        )

    async def ensure_instance(self, application_slug: str, application_version: str):
        self.ensure_calls.append((application_slug, application_version))
        return await self._fake_spawn(application_slug, application_version)

    async def spawn_instance(self, application_slug: str, application_version: str):
        self.spawn_calls.append((application_slug, application_version))
        return await self._fake_spawn(application_slug, application_version)

    async def remove_instance(self, instance_id: int) -> bool:
        instance = await self.adapter.get_instance_by_id(instance_id)
        if instance is None:
            return False
        return await self.adapter.delete_instance(instance.private_inbox)


def make_test_client(orchestrator: ContainerOrchestrator) -> TestClient:
    app = Litestar(
        route_handlers=[api_router],
        dependencies={
            "nats_broker": Provide(lambda: NatsBroker(), sync_to_thread=False),
            "orchestrator": Provide(lambda: orchestrator, sync_to_thread=False),
        },
    )
    return TestClient(app=app)


@pytest.fixture
def registered_dummy_cli(clean_registry_db):
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    db_row = sql_models.ApplicationSpecDB.from_pydantic_model(spec)
    return db_row.save_to_db()


INVOKE_BODY = {
    "application_slug": "dummy_cli",
    "application_version": "0.1.0",
    "command_name": "greet_and_sleep",
    "command_arguments": {"name": "Alice"},
}


def test_create_and_delete_container_instance(registered_dummy_cli):
    orchestrator = InMemoryOrchestrator()
    with make_test_client(orchestrator) as client:
        response = client.post(
            "/api/container-instances", json={"application_slug": "dummy_cli", "application_version": "0.1.0"}
        )
        assert response.status_code == 201
        payload = response.json()["payload"]["container_instances"][0]
        assert payload["client_id"] == "qcrbox_client_0xfake"
        assert orchestrator.spawn_calls == [("dummy_cli", "0.1.0")]

        instance_id = payload["id"]
        assert client.delete(f"/api/container-instances/{instance_id}").status_code == 204
        assert client.delete(f"/api/container-instances/{instance_id}").status_code == 404


def test_create_container_instance_error_mapping(registered_dummy_cli):
    with make_test_client(InMemoryOrchestrator()) as client:
        response = client.post(
            "/api/container-instances", json={"application_slug": "no_such_app", "application_version": "1.0"}
        )
        assert response.status_code == 404

    with make_test_client(InMemoryOrchestrator(failure=SpawnQuotaExceededError("quota"))) as client:
        response = client.post(
            "/api/container-instances", json={"application_slug": "dummy_cli", "application_version": "0.1.0"}
        )
        assert response.status_code == 409

    with make_test_client(InMemoryOrchestrator(failure=SpawnTimeoutError("too slow"))) as client:
        response = client.post(
            "/api/container-instances", json={"application_slug": "dummy_cli", "application_version": "0.1.0"}
        )
        assert response.status_code == 504

    with make_test_client(DisabledOrchestrator()) as client:
        response = client.post(
            "/api/container-instances", json={"application_slug": "dummy_cli", "application_version": "0.1.0"}
        )
        assert response.status_code == 503


def test_invoke_command_auto_spawns_when_no_instance_is_live(registered_dummy_cli):
    orchestrator = InMemoryOrchestrator()
    with make_test_client(orchestrator) as client:
        response = client.post("/api/commands", json=INVOKE_BODY)
        # The spawn succeeded (503 would mean the fast-fail path was taken); the request
        # then fails further down because the test NATS broker is not connected.
        assert response.status_code != 503
        assert orchestrator.ensure_calls == [("dummy_cli", "0.1.0")]


def test_invoke_command_still_fails_fast_with_disabled_orchestrator(registered_dummy_cli):
    """Phase-1 regression guard: without orchestration, no live instance means 503."""
    with make_test_client(DisabledOrchestrator()) as client:
        response = client.post("/api/commands", json=INVOKE_BODY)
        assert response.status_code == 503


def test_invoke_command_maps_spawn_timeout_to_504(registered_dummy_cli):
    orchestrator = InMemoryOrchestrator(failure=SpawnTimeoutError("too slow"))
    with make_test_client(orchestrator) as client:
        response = client.post("/api/commands", json=INVOKE_BODY)
        assert response.status_code == 504


def test_interactive_sessions_never_auto_spawn(registered_dummy_cli):
    orchestrator = InMemoryOrchestrator()
    with make_test_client(orchestrator) as client:
        response = client.post(
            "/api/interactive-sessions",
            json={"application_slug": "dummy_cli", "application_version": "0.1.0", "command_arguments": {}},
        )
        assert response.status_code == 503
        assert orchestrator.ensure_calls == []
