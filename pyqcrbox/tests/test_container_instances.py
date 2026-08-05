"""Tests for the container instance tracking (persistence layer + API, no NATS required)."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from pyqcrbox import sql_models
from pyqcrbox.registry.server.api import api_helpers
from pyqcrbox.services.persistence import SQLitePersistenceAdapter
from pyqcrbox.settings import settings
from pyqcrbox.sql_models import ContainerInstanceDB, ContainerInstanceStatusEnum

from .test_application_registration_api import DUMMY_CLI_SPEC_FILE


@pytest.fixture
def adapter() -> SQLitePersistenceAdapter:
    return SQLitePersistenceAdapter()


@pytest.fixture
async def registered_application(clean_registry_db, adapter) -> sql_models.ApplicationSpecDB:
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    return await adapter.save_application_spec(spec, private_routing_key="qcrbox_rk_0xtest")


@pytest.mark.anyio
async def test_save_container_instance_inserts_and_upserts(adapter, registered_application):
    instance = await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    assert instance.status == ContainerInstanceStatusEnum.IDLE

    # Re-registering with the same private inbox must update the existing row, not add a second one
    await adapter.update_instance_status("_INBOX.test.1", ContainerInstanceStatusEnum.BUSY)
    reregistered = await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    assert reregistered.id == instance.id
    assert reregistered.status == ContainerInstanceStatusEnum.IDLE

    with settings.db.get_session() as session:
        assert len(session.exec(select(ContainerInstanceDB)).all()) == 1


@pytest.mark.anyio
async def test_heartbeat_updates_last_seen_and_status(adapter, registered_application):
    instance = await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    first_seen = instance.last_seen

    updated = await adapter.upsert_instance_from_heartbeat(
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        application_slug="dummy_cli",
        application_version="0.1.0",
        status="busy",
        pyqcrbox_version="test-version",
    )
    assert updated.id == instance.id
    assert updated.status == ContainerInstanceStatusEnum.BUSY
    assert updated.last_seen >= first_seen


@pytest.mark.anyio
async def test_heartbeat_recreates_missing_instance_row(adapter, registered_application):
    """A heartbeat must self-heal the instance table, e.g. after a registry restart."""
    recreated = await adapter.upsert_instance_from_heartbeat(
        client_id="qcrbox_client_0x02",
        private_inbox="_INBOX.test.2",
        application_slug="dummy_cli",
        application_version="0.1.0",
        status="idle",
        pyqcrbox_version="test-version",
    )
    assert recreated is not None
    assert recreated.application_id == registered_application.id


@pytest.mark.anyio
async def test_heartbeat_for_unknown_application_is_ignored(adapter, clean_registry_db):
    result = await adapter.upsert_instance_from_heartbeat(
        client_id="qcrbox_client_0x03",
        private_inbox="_INBOX.test.3",
        application_slug="no_such_app",
        application_version="1.0",
        status="idle",
        pyqcrbox_version="test-version",
    )
    assert result is None
    with settings.db.get_session() as session:
        assert session.exec(select(ContainerInstanceDB)).all() == []


@pytest.mark.anyio
async def test_deregistration_deletes_instance(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    assert await adapter.delete_instance("_INBOX.test.1") is True
    assert await adapter.delete_instance("_INBOX.test.1") is False
    with settings.db.get_session() as session:
        assert session.exec(select(ContainerInstanceDB)).all() == []


@pytest.mark.anyio
async def test_sweeper_marks_stale_instances_gone_and_heartbeat_resurrects(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    # Backdate the heartbeat, then sweep
    with settings.db.get_session() as session:
        instance = session.exec(select(ContainerInstanceDB)).one()
        instance.last_seen = datetime.now() - timedelta(seconds=60)
        session.add(instance)
        session.commit()

    marked_gone = await adapter.mark_stale_instances_gone(datetime.now() - timedelta(seconds=15))
    assert marked_gone == 1
    with settings.db.get_session() as session:
        assert session.exec(select(ContainerInstanceDB)).one().status == ContainerInstanceStatusEnum.GONE

    assert await adapter.count_live_instances(registered_application.id) == 0

    # A new heartbeat resurrects the instance
    resurrected = await adapter.upsert_instance_from_heartbeat(
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        application_slug="dummy_cli",
        application_version="0.1.0",
        status="idle",
        pyqcrbox_version="test-version",
    )
    assert resurrected.status == ContainerInstanceStatusEnum.IDLE
    assert await adapter.count_live_instances(registered_application.id) == 1


@pytest.mark.anyio
async def test_retrieve_container_instances_with_filters(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    instances = api_helpers.retrieve_container_instances()
    assert len(instances) == 1
    assert instances[0].application_slug == "dummy_cli"
    assert instances[0].application_version == "0.1.0"
    assert instances[0].status == ContainerInstanceStatusEnum.IDLE

    assert api_helpers.retrieve_container_instances(application_slug="dummy_cli") == instances
    assert api_helpers.retrieve_container_instances(application_slug="no_such_app") == []


@pytest.mark.anyio
async def test_gui_url_lookup_by_private_inbox(adapter, registered_application):
    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.gui.1",
        pyqcrbox_version="test-version",
    )
    assert api_helpers.gui_url_for_private_inbox("_INBOX.gui.1") is None  # no gui_host set

    await adapter.set_instance_spawn_details(
        "qcrbox_client_0x01", "cafebabe" * 8, gui_host="dummy-cli-0x01.gui.qcrbox.localhost"
    )
    assert api_helpers.gui_url_for_private_inbox("_INBOX.gui.1") == "https://dummy-cli-0x01.gui.qcrbox.localhost/"

    await adapter.set_instance_spawn_details(
        "qcrbox_client_0x01", "cafebabe" * 8, gui_host="gui.qcrbox.localhost/dummy-cli-0x01"
    )
    assert api_helpers.gui_url_for_private_inbox("_INBOX.gui.1") == (
        "https://gui.qcrbox.localhost/dummy-cli-0x01/"
    )
    assert api_helpers.gui_url_for_private_inbox("_INBOX.unknown") is None


@pytest.mark.anyio
async def test_live_instance_gating_for_command_dispatch(adapter, registered_application):
    with pytest.raises(api_helpers.ApplicationNotFoundError):
        api_helpers.ensure_live_container_exists("no_such_app", "1.0")

    with pytest.raises(api_helpers.NoLiveContainerError):
        api_helpers.ensure_live_container_exists("dummy_cli", "0.1.0")

    await adapter.save_container_instance(
        application_id=registered_application.id,
        client_id="qcrbox_client_0x01",
        private_inbox="_INBOX.test.1",
        pyqcrbox_version="test-version",
    )
    # Does not raise anymore
    api_helpers.ensure_live_container_exists("dummy_cli", "0.1.0")
