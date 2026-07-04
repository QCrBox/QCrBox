from typing import Literal

from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxBasePayload

__all__ = ["DeregisterClient", "PayloadForDeregisterClient"]


class PayloadForDeregisterClient(QCrBoxBasePayload):
    client_id: str
    private_inbox: str
    reason: str = "client_shutdown"


class DeregisterClient(QCrBoxBaseAction):
    action: Literal["deregister_client"] = "deregister_client"
    payload: PayloadForDeregisterClient
