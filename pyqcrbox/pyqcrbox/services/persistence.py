from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import select

from pyqcrbox.logging import logger
from pyqcrbox.settings import settings
from pyqcrbox.sql_models import ApplicationSpecDB, ContainerInstanceDB, ContainerInstanceStatusEnum

if TYPE_CHECKING:
    from pyqcrbox.sql_models import ApplicationSpec


class BasePersistenceAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def save_application_spec(
        self, application_spec: "ApplicationSpec", private_routing_key: str | None = None
    ) -> ApplicationSpecDB | None:
        pass


class NatsPersistenceAdapter(BasePersistenceAdapter):
    async def save_application_spec(
        self, application_spec: "ApplicationSpec", private_routing_key: str | None = None
    ) -> ApplicationSpecDB | None:
        # kv_applications = await get_nats_key_value(bucket="applications")
        # nats_key = application_spec.nats_key
        # try:
        #     existing_application_spec = await kv_applications.get(nats_key)
        #     logger.warning(
        #         "TODO: an application with the same slug and version was registered before. "
        #         f"Verify that the new spec is consistent with the existing one: {existing_application_spec=}"
        #     )
        #     return
        # except nats.js.errors.KeyNotFoundError:
        #     pass

        # nats_value = application_spec.model_dump_json().encode()
        # await kv_applications.put(nats_key, nats_value)
        exc_msg = "Storing applications in NATS is not currently supported"
        raise NotImplementedError(exc_msg)


class SQLitePersistenceAdapter(BasePersistenceAdapter):
    async def save_application_spec(
        self, application_spec: "ApplicationSpec", private_routing_key: str | None = None
    ) -> ApplicationSpecDB:
        application_spec_db = ApplicationSpecDB.from_pydantic_model(
            application_spec, private_routing_key=private_routing_key
        )
        return application_spec_db.save_to_db()

    async def save_container_instance(
        self,
        application_id: int,
        client_id: str,
        private_inbox: str,
        pyqcrbox_version: str,
    ) -> ContainerInstanceDB:
        """Insert (or refresh) the container instance identified by `private_inbox`."""
        with settings.db.get_session() as session:
            instance = session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.private_inbox == private_inbox)
            ).first()
            if instance is None:
                instance = ContainerInstanceDB(
                    client_id=client_id,
                    private_inbox=private_inbox,
                    application_id=application_id,
                    pyqcrbox_version=pyqcrbox_version,
                )
            else:
                instance.client_id = client_id
                instance.application_id = application_id
                instance.pyqcrbox_version = pyqcrbox_version
                instance.status = ContainerInstanceStatusEnum.IDLE
            instance.last_seen = datetime.now()
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    async def upsert_instance_from_heartbeat(
        self,
        client_id: str,
        private_inbox: str,
        application_slug: str,
        application_version: str,
        status: str,
        pyqcrbox_version: str,
    ) -> ContainerInstanceDB | None:
        """Refresh `last_seen`/`status` for a heartbeating client.

        Recreates the instance row if it is missing (e.g. after a registry
        restart) and the application can be resolved by slug/version.
        Returns None if the row is missing and the application is unknown.
        """
        with settings.db.get_session() as session:
            instance = session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.private_inbox == private_inbox)
            ).first()
            if instance is None:
                application = session.exec(
                    select(ApplicationSpecDB).where(
                        ApplicationSpecDB.slug == application_slug,
                        ApplicationSpecDB.version == application_version,
                    )
                ).first()
                if application is None:
                    return None
                instance = ContainerInstanceDB(
                    client_id=client_id,
                    private_inbox=private_inbox,
                    application_id=application.id,
                    pyqcrbox_version=pyqcrbox_version,
                )
            instance.status = ContainerInstanceStatusEnum(status)
            instance.last_seen = datetime.now()
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    async def get_application(self, application_slug: str, application_version: str) -> ApplicationSpecDB | None:
        with settings.db.get_session() as session:
            return session.exec(
                select(ApplicationSpecDB).where(
                    ApplicationSpecDB.slug == application_slug,
                    ApplicationSpecDB.version == application_version,
                )
            ).first()

    async def get_instance_by_id(self, instance_id: int) -> ContainerInstanceDB | None:
        with settings.db.get_session() as session:
            return session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.id == instance_id)
            ).first()

    async def get_instance_by_client_id(self, client_id: str) -> ContainerInstanceDB | None:
        with settings.db.get_session() as session:
            return session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.client_id == client_id)
            ).first()

    async def get_live_instance(self, application_slug: str, application_version: str) -> ContainerInstanceDB | None:
        with settings.db.get_session() as session:
            return session.exec(
                select(ContainerInstanceDB)
                .join(ApplicationSpecDB, ContainerInstanceDB.application_id == ApplicationSpecDB.id)
                .where(
                    ApplicationSpecDB.slug == application_slug,
                    ApplicationSpecDB.version == application_version,
                    ContainerInstanceDB.status != ContainerInstanceStatusEnum.GONE,
                )
            ).first()

    async def set_instance_spawn_details(
        self,
        client_id: str,
        docker_container_id: str,
        gui_host: str | None = None,
        owner_user_id: str | None = None,
    ) -> None:
        """Record orchestrator-spawn metadata on the instance row after registration."""
        with settings.db.get_session() as session:
            instance = session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.client_id == client_id)
            ).first()
            if instance is None:
                logger.warning(f"Cannot set spawn details for unknown client: {client_id!r}")
                return
            instance.docker_container_id = docker_container_id
            instance.gui_host = gui_host
            instance.owner_user_id = owner_user_id
            session.add(instance)
            session.commit()

    async def application_has_interactive_commands(self, application_id: int) -> bool:
        from pyqcrbox.sql_models import CommandSpecDB
        from pyqcrbox.sql_models.command_spec.base_command_spec import ImplementedAs

        with settings.db.get_session() as session:
            interactive_command = session.exec(
                select(CommandSpecDB).where(
                    CommandSpecDB.application_id == application_id,
                    CommandSpecDB.implemented_as == ImplementedAs.interactive_session,
                )
            ).first()
            return interactive_command is not None

    async def get_instance_by_private_inbox(self, private_inbox: str) -> ContainerInstanceDB | None:
        with settings.db.get_session() as session:
            return session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.private_inbox == private_inbox)
            ).first()

    async def update_instance_status(self, private_inbox: str, status: ContainerInstanceStatusEnum) -> None:
        with settings.db.get_session() as session:
            instance = session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.private_inbox == private_inbox)
            ).first()
            if instance is None:
                logger.warning(f"Cannot update status of unknown container instance: {private_inbox!r}")
                return
            instance.status = status
            session.add(instance)
            session.commit()

    async def delete_instance(self, private_inbox: str) -> bool:
        with settings.db.get_session() as session:
            instance = session.exec(
                select(ContainerInstanceDB).where(ContainerInstanceDB.private_inbox == private_inbox)
            ).first()
            if instance is None:
                return False
            session.delete(instance)
            session.commit()
            return True

    async def mark_stale_instances_gone(self, cutoff: datetime) -> int:
        """Mark instances whose last heartbeat is older than `cutoff` as GONE."""
        with settings.db.get_session() as session:
            stale_instances = session.exec(
                select(ContainerInstanceDB).where(
                    ContainerInstanceDB.last_seen < cutoff,
                    ContainerInstanceDB.status != ContainerInstanceStatusEnum.GONE,
                )
            ).all()
            for instance in stale_instances:
                logger.info(
                    f"Marking container instance as gone (no heartbeat since {instance.last_seen}): "
                    f"client_id={instance.client_id!r}, private_inbox={instance.private_inbox!r}"
                )
                instance.status = ContainerInstanceStatusEnum.GONE
                session.add(instance)
            session.commit()
            return len(stale_instances)

    async def count_live_instances(self, application_id: int) -> int:
        with settings.db.get_session() as session:
            instances = session.exec(
                select(ContainerInstanceDB).where(
                    ContainerInstanceDB.application_id == application_id,
                    ContainerInstanceDB.status != ContainerInstanceStatusEnum.GONE,
                )
            ).all()
            return len(instances)
