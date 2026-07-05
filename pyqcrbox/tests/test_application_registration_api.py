"""Tests for registering application specs via the REST API (no NATS required)."""

from pathlib import Path

import pytest
from faststream.nats import NatsBroker
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient

from pyqcrbox import sql_models
from pyqcrbox.registry.server.api.api_endpoints import api_router
from pyqcrbox.registry.server.api.identity import get_current_user
from pyqcrbox.services.orchestrator import DisabledOrchestrator
from pyqcrbox.services.persistence import SQLitePersistenceAdapter
from pyqcrbox.settings import settings
from pyqcrbox.sql_models import ApplicationSpec

DUMMY_CLI_SPEC_FILE = (
    Path(__file__).parent / ".." / ".." / "services" / "applications" / "dummy_cli" / "config_dummy_cli.yaml"
).resolve()


@pytest.fixture
def sample_application_spec() -> ApplicationSpec:
    return ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)


@pytest.fixture
def api_client(clean_registry_db) -> TestClient:
    app = Litestar(
        route_handlers=[api_router],
        dependencies={
            # An unconnected broker: the tested endpoints fail fast before any NATS traffic
            "nats_broker": Provide(lambda: NatsBroker(), sync_to_thread=False),
            # Orchestration disabled: preserves the fail-fast 404/503 behaviour under test
            "orchestrator": Provide(lambda: DisabledOrchestrator(), sync_to_thread=False),
            "current_user": Provide(get_current_user),
        },
    )
    with TestClient(app=app) as client:
        yield client


def test_register_application_via_api(api_client, sample_application_spec):
    response = api_client.post("/api/applications", json=sample_application_spec.model_dump(mode="json"))
    assert response.status_code == 201

    response = api_client.get("/api/applications")
    assert response.status_code == 200
    applications = response.json()["payload"]["applications"]
    assert len(applications) == 1
    assert applications[0]["slug"] == "dummy_cli"
    assert applications[0]["num_live_instances"] == 0
    command_names = {cmd["name"] for cmd in applications[0]["commands"]}
    assert "greet_and_sleep" in command_names


def test_reregistering_application_is_idempotent(api_client, sample_application_spec):
    payload = sample_application_spec.model_dump(mode="json")
    assert api_client.post("/api/applications", json=payload).status_code == 201
    assert api_client.post("/api/applications", json=payload).status_code == 201

    applications = api_client.get("/api/applications").json()["payload"]["applications"]
    assert len(applications) == 1


def test_register_application_with_version_mismatch_is_rejected(api_client, sample_application_spec):
    spec_with_wrong_version = sample_application_spec.model_copy(update={"pyqcrbox_version": "0.0.0-mismatch"})
    response = api_client.post("/api/applications", json=spec_with_wrong_version.model_dump(mode="json"))
    assert response.status_code == 409

    applications = api_client.get("/api/applications").json()["payload"]["applications"]
    assert applications == []


def test_invoke_command_for_unknown_application_returns_404(api_client):
    response = api_client.post(
        "/api/commands",
        json={
            "application_slug": "no_such_app",
            "application_version": "1.0",
            "command_name": "greet_and_sleep",
            "command_arguments": {"name": "Alice"},
        },
    )
    assert response.status_code == 404


def test_invoke_command_without_live_container_returns_503(api_client, sample_application_spec):
    assert (
        api_client.post("/api/applications", json=sample_application_spec.model_dump(mode="json")).status_code == 201
    )
    response = api_client.post(
        "/api/commands",
        json={
            "application_slug": "dummy_cli",
            "application_version": "0.1.0",
            "command_name": "greet_and_sleep",
            "command_arguments": {"name": "Alice"},
        },
    )
    assert response.status_code == 503
    assert api_client.post(
        "/api/interactive-sessions",
        json={
            "application_slug": "dummy_cli",
            "application_version": "0.1.0",
            "command_arguments": {},
        },
    ).status_code == 503


@pytest.mark.anyio
async def test_registration_persists_real_private_routing_key(clean_registry_db, sample_application_spec):
    """Regression test: the routing key from the registration payload must be stored, not a hardcoded default."""
    adapter = SQLitePersistenceAdapter()
    saved = await adapter.save_application_spec(sample_application_spec, private_routing_key="qcrbox_rk_0xdeadbeef")

    from sqlmodel import select

    with settings.db.get_session() as session:
        row = session.exec(
            select(sql_models.ApplicationSpecDB).where(sql_models.ApplicationSpecDB.id == saved.id)
        ).one()
        assert row.private_routing_key == "qcrbox_rk_0xdeadbeef"
