# SPDX-License-Identifier: MPL-2.0

from pyqcrbox.settings import settings

from .cli_helpers import add_cli_option_to_enable_or_disable_components, add_verbose_option
from .docker_project import DockerProject
from .doit_helpers import make_task, run_tasks
from .qcrbox_helpers import (
    QCrBoxSubprocessError,
    get_mkdocs_config_file_path,
    get_repo_root,
    prettyprint_called_process_error,
)

if not settings.cli.disable_rich:
    from rich_click import RichCommand as ClickCommandCls
    from rich_click import RichGroup as ClickGroupCls
else:
    from click import Command as ClickCommandCls
    from click import Group as ClickGroupCls


class NaturalOrderGroup(ClickGroupCls):
    def list_commands(self, ctx):
        return self.commands.keys()
