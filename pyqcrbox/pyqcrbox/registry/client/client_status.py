from enum import StrEnum

from pyqcrbox import logger


class ClientStatusEnum(StrEnum):
    IDLE = "idle"
    PENDING = "pending"
    BUSY = "BUSY"
    INTERNAL_ERROR = "internal_error"


class ClientStatus:
    def __init__(self, initial_status: ClientStatusEnum | str = ClientStatusEnum.IDLE):
        self._status = ClientStatusEnum(initial_status)

    @property
    def status(self):
        return self._status

    @property
    def is_available(self) -> bool:
        return self.status == ClientStatusEnum.IDLE

    def set_pending(self) -> None:
        if self.status != ClientStatusEnum.IDLE:
            raise RuntimeError(f"Cannot set status to 'pending' from '{self.status} (current status must be 'idle').")
        logger.debug("Setting client status to 'pending'")
        self._status = ClientStatusEnum.PENDING

    def set_idle(self) -> None:
        logger.debug("Setting client status to 'idle'")
        self._status = ClientStatusEnum.IDLE

    def set_busy(self) -> None:
        if self.status != ClientStatusEnum.PENDING:
            raise RuntimeError(f"Cannot set status to 'busy' from '{self.status} (current status must be 'pending').")
        logger.debug("Setting client status to 'busy'")
        self._status = ClientStatusEnum.BUSY
