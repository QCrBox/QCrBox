from abc import ABCMeta, abstractmethod
from typing import ClassVar

from pyqcrbox.sql_models import ContainerInstanceDB

__all__ = [
    "ApplicationNotRegisteredError",
    "ContainerOrchestrator",
    "DisabledOrchestrator",
    "InstanceNotManagedError",
    "OrchestratorDisabledError",
    "OrchestratorError",
    "SpawnNotPossibleError",
    "SpawnQuotaExceededError",
    "SpawnTimeoutError",
]


class OrchestratorError(Exception):
    """Base class for container orchestration errors."""


class OrchestratorDisabledError(OrchestratorError):
    """Raised when container orchestration is disabled in the settings."""


class SpawnNotPossibleError(OrchestratorError):
    """Raised when an application cannot be spawned (e.g. no docker image registered)."""


class ApplicationNotRegisteredError(SpawnNotPossibleError):
    """Raised when trying to spawn a container for an application unknown to the registry."""


class SpawnQuotaExceededError(OrchestratorError):
    """Raised when spawning would exceed the per-application instance quota."""


class SpawnTimeoutError(OrchestratorError):
    """Raised when a spawned container did not register within the timeout."""


class InstanceNotManagedError(OrchestratorError):
    """Raised when an instance is not managed by the orchestrator (e.g. compose-started)."""


class ContainerOrchestrator(metaclass=ABCMeta):
    """Interface for spawning and removing application containers on demand.

    Implementations exist per deployment target (currently Docker via
    `DockerOrchestrator`; a Kubernetes backend can be added later).
    """

    enabled: ClassVar[bool] = True

    async def startup(self) -> None:  # noqa: B027
        """Perform any one-off initialisation (e.g. environment discovery)."""

    async def shutdown(self) -> None:  # noqa: B027
        """Release any resources held by the orchestrator."""

    @abstractmethod
    async def ensure_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        """Return a live container instance for the application, spawning one only if none exists.

        A newly spawned instance is attributed to `owner` (the acting user), if known.
        """

    @abstractmethod
    async def spawn_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        """Spawn an additional container instance (subject to the per-application quota)."""

    @abstractmethod
    async def remove_instance(self, instance_id: int) -> bool:
        """Stop and remove a container instance managed by the orchestrator.

        Returns True on success; raises `InstanceNotManagedError` for instances
        the orchestrator did not spawn and cannot associate with a container.
        Returns False if no instance with the given id exists.
        """


class DisabledOrchestrator(ContainerOrchestrator):
    """Null implementation used when orchestration is disabled (static container setup)."""

    enabled = False

    async def ensure_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        raise OrchestratorDisabledError("Container orchestration is disabled")

    async def spawn_instance(
        self, application_slug: str, application_version: str, owner: str | None = None
    ) -> ContainerInstanceDB:
        raise OrchestratorDisabledError("Container orchestration is disabled")

    async def remove_instance(self, instance_id: int) -> bool:
        raise OrchestratorDisabledError("Container orchestration is disabled")
