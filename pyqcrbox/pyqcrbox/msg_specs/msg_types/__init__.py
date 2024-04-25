from .client_side import *
from .initiate_command_execution import *
from .server_side import *
from .shared import *

# Store the local variables representing QCrBox actions so that we can later
# construct a lookup for them.
_qcrbox_actions = [x for x in locals().values() if "action" in getattr(x, "model_fields", ())]
