from pathlib import Path

from pyqcrbox.helpers import import_all_submodules

from .base_message_dispatcher import client_side_message_dispatcher

CURRENT_DIRECTORY = Path(__file__).parent

# Import all submodules so that the message handlers defined inside them
# are automatically registered with the 'root' message_dispatcher function.
import_all_submodules(parent_dir=CURRENT_DIRECTORY, parent_package_name=__name__)
