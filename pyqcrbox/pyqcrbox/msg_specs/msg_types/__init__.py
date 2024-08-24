from .client_side import *
from .initiate_command_execution import *
from .server_side import *
from .shared import *

# Store the local variables representing QCrBox actions/responses so that we can
# later construct a lookup for them.
_qcrbox_actions = [x for x in locals().values() if "action" in getattr(x, "model_fields", ())]
_qcrbox_responses = [x for x in locals().values() if "response_to" in getattr(x, "model_fields", ())]
