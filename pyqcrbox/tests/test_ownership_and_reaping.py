"""Tests for GUI ownership authorization, targeted dispatch subjects, and reaping helpers."""

from datetime import datetime, timedelta

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import TestClient

from pyqcrbox import msg_specs, sql_models
from pyqcrbox.registry.server.api.api_endpoints import api_router
from pyqcrbox.registry.server.api.identity import get_current_user
from pyqcrbox.services.persistence import SQLitePersistenceAdapter
from pyqcrbox.settings import settings
from pyqcrbox.sql_models import ContainerInstanceStatusEnum

from .test_application_registration_api import DUMMY_CLI_SPEC_FILE

GUI_HOST = "dummy-cli-0xtest.gui.qcrbox.localhost"


@pytest.fixture
def adapter() -> SQLitePersistenceAdapter:
    return SQLitePersistenceAdapter()


@pytest.fixture
async def registered_application(clean_registry_db, adapter) -> sql_models.ApplicationSpecDB:
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    return await adapter.save_application_spec(spec)


async def seed_instance(adapter, application_id, owner=None, gui_host=GUI_HOST, inbox="_INBOX.own.1"):
    await adapter.save_container_instance(
        application_id=application_id,
        client_id=f"qcrbox_client_{inbox}",
        private_inbox=inbox,
        pyqcrbox_version="test-version",
    )
    await adapter.set_instance_spawn_details(
        f"qcrbox_client_{inbox}", "c" * 64, gui_host=gui_host, owner_user_id=owner
    )


@pytest.fixture
def auth_client():
    app = Litestar(route_handlers=[api_router], dependencies={"current_user": Provide(get_current_user)})
    with TestClient(app=app) as client:
        yield client


def gui_auth_status(client, forwarded_host=None, remote_user=None) -> int:
    headers = {}
    if forwarded_host:
        headers["X-Forwarded-Host"] = forwarded_host
    if remote_user:
        headers["Remote-User"] = remote_user
    return client.get("/api/auth/gui", headers=headers).status_code


@pytest.mark.anyio
async def test_gui_auth_owner_match(adapter, registered_application, auth_client):
    await seed_instance(adapter, registered_application.id, owner="alice")
    assert gui_auth_status(auth_client, GUI_HOST, "alice") == 200


@pytest.mark.anyio
async def test_gui_auth_owner_mismatch(adapter, registered_application, auth_client):
    await seed_instance(adapter, registered_application.id, owner="alice")
    assert gui_auth_status(auth_client, GUI_HOST, "bob") == 403


@pytest.mark.anyio
async def test_gui_auth_ownerless_open_to_authenticated_users(adapter, registered_application, auth_client):
    await seed_instance(adapter, registered_application.id, owner=None)
    assert gui_auth_status(auth_client, GUI_HOST, "anyone") == 200


@pytest.mark.anyio
async def test_gui_auth_unknown_host_and_missing_identity(adapter, registered_application, auth_client):
    await seed_instance(adapter, registered_application.id, owner="alice")
    assert gui_auth_status(auth_client, "unknown.gui.qcrbox.localhost", "alice") == 403
    assert gui_auth_status(auth_client, GUI_HOST, remote_user=None) == 403
    assert gui_auth_status(auth_client, forwarded_host=None, remote_user="alice") == 403


def test_invocation_subject_selection():
    msg = msg_specs.InvokeCommandNATS(
        application_slug="dummy_cli", application_version="0.1.0", command_name="x", command_arguments={}
    )
    assert msg.invocation_request_subject == "client.cmd.handle_invocation_request.dummy_cli.0_1_0"

    targeted = msg_specs.InvokeCommandNATS(
        application_slug="dummy_cli",
        application_version="0.1.0",
        command_name="x",
        command_arguments={},
        target_private_inbox="_INBOX.abc",
    )
    assert targeted.invocation_request_subject == "_INBOX.abc.cmd.handle_invocation_request"


@pytest.mark.anyio
async def test_status_changed_at_moves_only_on_transitions(adapter, registered_application):
    await seed_instance(adapter, registered_application.id, inbox="_INBOX.trans.1")
    instance = await adapter.get_instance_by_private_inbox("_INBOX.trans.1")
    initial_stamp = instance.status_changed_at

    # Heartbeat with the same status: last_seen moves, status_changed_at does not
    await adapter.upsert_instance_from_heartbeat(
        client_id=instance.client_id,
        private_inbox=instance.private_inbox,
        application_slug="dummy_cli",
        application_version="0.1.0",
        status="idle",
        pyqcrbox_version="test-version",
    )
    unchanged = await adapter.get_instance_by_private_inbox("_INBOX.trans.1")
    assert unchanged.status_changed_at == initial_stamp
    assert unchanged.last_seen >= instance.last_seen

    # A transition stamps it
    await adapter.update_instance_status("_INBOX.trans.1", ContainerInstanceStatusEnum.BUSY)
    changed = await adapter.get_instance_by_private_inbox("_INBOX.trans.1")
    assert changed.status_changed_at > initial_stamp


@pytest.mark.anyio
async def test_reapable_and_purgeable_selection(adapter, registered_application):
    # Managed idle instance, backdated -> reapable
    await seed_instance(adapter, registered_application.id, inbox="_INBOX.reap.1", gui_host=None)
    # Unmanaged idle instance (no docker_container_id) -> never reaped
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_unmanaged",
        private_inbox="_INBOX.unmanaged.1",
        pyqcrbox_version="test-version",
    )
    with settings.db.get_session() as session:
        from sqlmodel import select

        for instance in session.exec(select(sql_models.ContainerInstanceDB)).all():
            instance.status_changed_at = datetime.now() - timedelta(hours=2)
            session.add(instance)
        session.commit()

    reapable = await adapter.get_reapable_idle_instances(datetime.now() - timedelta(hours=1))
    assert [i.private_inbox for i in reapable] == ["_INBOX.reap.1"]

    # Gone rows older than the cutoff are purgeable
    await adapter.mark_stale_instances_gone(datetime.now() + timedelta(seconds=1))
    with settings.db.get_session() as session:
        from sqlmodel import select

        for instance in session.exec(select(sql_models.ContainerInstanceDB)).all():
            instance.last_seen = datetime.now() - timedelta(hours=2)
            session.add(instance)
        session.commit()
    purgeable = await adapter.get_purgeable_gone_instances(datetime.now() - timedelta(hours=1))
    assert {i.private_inbox for i in purgeable} == {"_INBOX.reap.1", "_INBOX.unmanaged.1"}