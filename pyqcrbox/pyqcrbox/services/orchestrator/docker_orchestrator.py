import asyncio
import platform
import re
import time
from collections.abc import Callable

from pyqcrbox.helpers import generate_client_id, sanitize_for_nats_subject
from pyqcrbox.logging import logger
from pyqcrbox.settings import settings
from pyqcrbox.sql_models import ApplicationSpecDB, ContainerInstanceDB, ContainerInstanceStatusEnum

from ..persistence import SQLitePersistenceAdapter
from .base import (
    ApplicationNotRegisteredError,
    ContainerOrchestrator,
    InstanceNotManagedError,
    SpawnNotPossibleError,
    SpawnQuotaExceededError,
    SpawnTimeoutError,
)

__all__ = ["DockerOrchestrator"]


class DockerOrchestrator(ContainerOrchestrator):
    """Spawns application containers via the Docker API (through the socket proxy).

    Spawned containers are correlated with their registry registration through
    the QCRBOX_CLIENT_ID environment variable (honoured by `QCrBoxClient`) and
    are labelled `<label_prefix>.spawned=true` so that `qcb down` can clean
    them up.
    """

    def __init__(
        self,
        persistence: SQLitePersistenceAdapter | None = None,
        orchestrator_settings=None,
        docker_factory: Callable | None = None,
    ):
        self._settings = orchestrator_settings or settings.orchestrator
        self._persistence = persistence or SQLitePersistenceAdapter()
        self._docker_factory = docker_factory
        self._docker = None
        self._spawn_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._network_name: str | None = self._settings.network_name

    async def _get_docker(self):
        if self._docker is None:
            if self._docker_factory is not None:
                self._docker = self._docker_factory()
            else:
                # Imported lazily: aiodocker is only installed in the registry image
                # (the `orchestrator` extra), not in application containers.
                import aiodocker

                self._docker = aiodocker.Docker(url=self._settings.docker_host)
        return self._docker

    async def startup(self) -> None:
        """Discover the docker network to attach spawned containers to.

        Inspects the registry's own container (hostname == container id unless
        a `hostname:` is set in the compose file) and picks its qcrbox network.
        Falls back to the configured fallback network name.
        """
        if self._network_name is not None:
            return
        try:
            docker = await self._get_docker()
            own_container = await docker.containers.container(platform.node()).show()
            networks = list(own_container["NetworkSettings"]["Networks"])
            self._network_name = next((n for n in networks if n.endswith("qcrbox-net")), networks[0])
            logger.info(f"Orchestrator will attach spawned containers to network {self._network_name!r}")
        except Exception as exc:
            self._network_name = self._settings.fallback_network_name
            logger.warning(
                f"Could not discover the docker network from the registry's own container ({exc}); "
                f"falling back to {self._network_name!r}"
            )

    async def shutdown(self) -> None:
        if self._docker is not None:
            await self._docker.close()
            self._docker = None

    def _get_spawn_lock(self, application_slug: str, application_version: str) -> asyncio.Lock:
        return self._spawn_locks.setdefault((application_slug, application_version), asyncio.Lock())

    async def ensure_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        async with self._get_spawn_lock(application_slug, application_version):
            # A concurrent request may have spawned an instance while we waited for the lock
            existing_instance = await self._persistence.get_live_instance(application_slug, application_version)
            if existing_instance is not None:
                return existing_instance
            return await self._spawn(application_slug, application_version, owner=owner)

    async def spawn_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        async with self._get_spawn_lock(application_slug, application_version):
            application = await self._get_application_or_raise(application_slug, application_version)
            num_live = await self._persistence.count_live_instances(application.id)
            if num_live >= self._settings.max_instances_per_app:
                raise SpawnQuotaExceededError(
                    f"Cannot spawn another container for {application_slug!r} (version {application_version!r}): "
                    f"the quota of {self._settings.max_instances_per_app} live instances is reached"
                )
            return await self._spawn(application_slug, application_version, application=application, owner=owner)

    async def remove_instance(self, instance_id: int) -> bool:
        instance = await self._persistence.get_instance_by_id(instance_id)
        if instance is None:
            return False

        docker = await self._get_docker()
        container_id = instance.docker_container_id
        if container_id is None:
            # The docker container id can be lost when a heartbeat recreates the row
            # after a registry restart; try to re-associate via the spawn label.
            label_filter = f"{self._settings.label_prefix}.client_id={instance.client_id}"
            candidates = await docker.containers.list(all=True, filters={"label": [label_filter]})
            if not candidates:
                raise InstanceNotManagedError(
                    f"Container instance {instance_id} was not spawned by the orchestrator "
                    "(no associated docker container)"
                )
            container_id = candidates[0].id

        logger.info(f"Removing container {container_id[:12]} for instance {instance_id}")
        try:
            await docker.containers.container(container_id).delete(force=True)
        except Exception as exc:
            # The container may already be gone (e.g. removed externally, or a
            # stale 'gone' row); a missing container must not block deleting
            # the instance record.
            if getattr(exc, "status", None) != 404:
                raise
            logger.info(f"Container {container_id[:12]} was already removed")
        await self._persistence.delete_instance(instance.private_inbox)
        return True

    async def _get_application_or_raise(self, application_slug: str, application_version: str) -> ApplicationSpecDB:
        application = await self._persistence.get_application(application_slug, application_version)
        if application is None:
            raise ApplicationNotRegisteredError(
                f"Application not registered: {application_slug!r} (version {application_version!r})"
            )
        return application

    async def _spawn(
        self,
        application_slug: str,
        application_version: str,
        application: ApplicationSpecDB | None = None,
        owner: str | None = None,
    ) -> ContainerInstanceDB:
        if application is None:
            application = await self._get_application_or_raise(application_slug, application_version)
        if not application.docker_image:
            raise SpawnNotPossibleError(
                f"No docker image registered for {application_slug!r} (version {application_version!r}); "
                "re-register the application via 'qcb register' to enable on-demand spawning"
            )
        if self._network_name is None:
            await self.startup()

        client_id = generate_client_id()
        is_gui_application = await self._persistence.application_has_interactive_commands(application.id)
        gui_host = self._build_gui_host(application.slug, client_id) if is_gui_application else None
        container_config = self._build_container_config(application, client_id, gui_host=gui_host)
        container_name = (
            f"qcrbox-spawned-{sanitize_for_nats_subject(application_slug)}-{client_id[-8:]}"
        )

        logger.info(
            f"Spawning container for {application_slug!r} (version {application_version!r}) "
            f"from image {application.docker_image!r} as {container_name!r}"
            + (f" with GUI route {gui_host!r}" if gui_host else "")
        )
        docker = await self._get_docker()
        container = await docker.containers.create(config=container_config, name=container_name)
        try:
            await container.start()
            instance = await self._wait_for_registration(client_id)
        except BaseException:
            logger.warning(f"Spawn of {container_name!r} failed; removing the container")
            await container.delete(force=True)
            raise

        await self._persistence.set_instance_spawn_details(
            client_id, container.id, gui_host=gui_host, owner_user_id=owner
        )
        instance.docker_container_id = container.id
        instance.gui_host = gui_host
        instance.owner_user_id = owner
        logger.info(
            f"Spawned container {container.id[:12]} is registered and ready "
            f"(client_id={client_id!r}, owner={owner!r})"
        )
        return instance

    def _build_gui_host(self, application_slug: str, client_id: str) -> str:
        # A single DNS label (covered by the Authelia wildcard rule for *.gui.<domain>);
        # slugs may contain characters that are invalid in hostnames (e.g. underscores).
        slug_label = re.sub(r"[^a-z0-9-]", "-", application_slug.lower()).strip("-")
        return f"{slug_label}-{client_id[-8:]}.gui.{self._settings.gui_domain}"

    def _build_container_config(
        self, application: ApplicationSpecDB, client_id: str, gui_host: str | None = None
    ) -> dict:
        s = self._settings
        host_config = {
            "NetworkMode": self._network_name,
            "RestartPolicy": {"Name": "unless-stopped"},
        }
        if s.use_syslog_logging:
            host_config["LogConfig"] = {
                "Type": "syslog",
                "Config": {"syslog-address": s.syslog_address, "tag": application.slug},
            }
        labels = {
            f"{s.label_prefix}.spawned": "true",
            f"{s.label_prefix}.application_slug": application.slug,
            f"{s.label_prefix}.application_version": application.version,
            f"{s.label_prefix}.client_id": client_id,
        }
        if gui_host is not None:
            labels.update(self._build_traefik_labels(client_id, gui_host))
        return {
            "Image": application.docker_image,
            "Env": [
                f"QCRBOX_CLIENT_ID={client_id}",
                f"QCRBOX_APPLICATION_DISPLAY_NAME={application.name}",
                f"QCRBOX__NATS__HOST={s.nats_host}",
                f"QCRBOX__REGISTRY__SERVER__HOST={s.registry_host}",
                f"QCRBOX__REGISTRY__SERVER__PORT={s.registry_port}",
            ],
            "Labels": labels,
            "HostConfig": host_config,
        }

    def _build_traefik_labels(self, client_id: str, gui_host: str) -> dict[str, str]:
        """Per-instance Traefik route for the container's noVNC GUI.

        Mirrors the static subdomain route pattern of the compose-started GUI
        apps (router behind the `authelia-auth` forwardAuth middleware, plus a
        redirect from the bare host to the noVNC page). Traefik's docker
        provider picks the labels up automatically when the container starts.
        """
        name = f"qcrbox-gui-{client_id[-8:]}"
        vnc_url = (
            f"https://{gui_host}/vnc.html?path=vnc&autoconnect=true&resize=remote&reconnect=true&show_dot=true"
        )
        return {
            "traefik.enable": "true",
            f"traefik.http.routers.{name}.rule": f"Host(`{gui_host}`)",
            f"traefik.http.routers.{name}.entrypoints": "websecure",
            f"traefik.http.routers.{name}.middlewares": f"authelia-auth,{name}-redirect",
            f"traefik.http.routers.{name}.service": name,
            f"traefik.http.middlewares.{name}-redirect.redirectregex.regex": f"^https://{re.escape(gui_host)}/?$",
            f"traefik.http.middlewares.{name}-redirect.redirectregex.replacement": vnc_url,
            f"traefik.http.services.{name}.loadbalancer.server.scheme": "http",
            f"traefik.http.services.{name}.loadbalancer.server.port": str(self._settings.gui_container_port),
        }

    async def _wait_for_registration(self, client_id: str) -> ContainerInstanceDB:
        deadline = time.monotonic() + self._settings.spawn_timeout
        while time.monotonic() < deadline:
            instance = await self._persistence.get_instance_by_client_id(client_id)
            if instance is not None and instance.status != ContainerInstanceStatusEnum.GONE:
                return instance
            await asyncio.sleep(self._settings.poll_interval)
        raise SpawnTimeoutError(
            f"Spawned container (client_id={client_id!r}) did not register within "
            f"{self._settings.spawn_timeout:.0f}s"
        )
