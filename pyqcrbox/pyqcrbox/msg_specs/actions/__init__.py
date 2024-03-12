from .accept_command_invocation import *
from .invoke_command import *
from .register_application import *

# Store the local variables so that we can later construct
# a lookup for the valid QCrBox actions.
_qcrbox_actions_and_other_local_vars = locals().values()
