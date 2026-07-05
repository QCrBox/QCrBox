from pyqcrbox.settings import settings

from .base import (
    ApplicationNotRegisteredError,
    ContainerOrchestrator,
    DisabledOrchestrator,
    InstanceNotManagedError,
    OrchestratorDisabledError,
    OrchestratorError,
    SpawnNotPossibleError,
    SpawnQuotaExceededError,
    SpawnTimeoutError,
)
from .docker_orchestrator import DockerOrchestrator

__all__ = [
    "ApplicationNotRegisteredError",
    "ContainerOrchestrator",
    "DisabledOrchestrator",
    "DockerOrchestrator",
    "InstanceNotManagedError",
    "OrchestratorDisabledError",
    "OrchestratorError",
    "SpawnNotPossibleError",
    "SpawnQuotaExceededError",
    "SpawnTimeoutError",
    "create_orchestrator",
]

_orchestrator_singleton: ContainerOrchestrator | None = None


def create_orchestrator() -> ContainerOrchestrator:
    """Return the process-wide orchestrator (Docker-backed or disabled, per settings).

    A singleton so that the per-application spawn locks are shared between all
    consumers (API handlers, startup hooks).
    """
    global _orchestrator_singleton
    if _orchestrator_singleton is None:
        _orchestrator_singleton = DockerOrchestrator() if settings.orchestrator.enabled else DisabledOrchestrator()
    return _orchestrator_singleton
