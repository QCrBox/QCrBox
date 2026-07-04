from typing import Literal

from pyqcrbox.msg_specs.base import QCrBoxBaseAction, QCrBoxBasePayload

__all__ = ["ClientHeartbeat", "PayloadForClientHeartbeat"]


class PayloadForClientHeartbeat(QCrBoxBasePayload):
    client_id: str
    private_inbox: str
    application_slug: str
    application_version: str
    status: str
    pyqcrbox_version: str


class ClientHeartbeat(QCrBoxBaseAction):
    action: Literal["client_heartbeat"] = "client_heartbeat"
    payload: PayloadForClientHeartbeat
