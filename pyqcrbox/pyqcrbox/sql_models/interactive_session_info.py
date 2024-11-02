from pyqcrbox.msg_specs import CommandExecutionRequestNATS
from pyqcrbox.sql_models import QCrBoxPydanticBaseModel

__all__ = ["InteractiveSessionInfo"]


class InteractiveSessionInfo(QCrBoxPydanticBaseModel):
    session_id: str
    client_private_inbox: str
    cmd_execution_request: CommandExecutionRequestNATS
