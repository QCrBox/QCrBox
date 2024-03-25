# SPDX-License-Identifier: MPL-2.0

import click

from .cli_helpers import add_cli_option_enable_disable_components, add_verbose_option
from .docker_project import DockerProject
from .doit_helpers import make_task, run_tasks
from .qcrbox_helpers import (
    QCrBoxSubprocessError,
    get_mkdocs_config_file_path,
    get_repo_root,
    prettyprint_called_process_error,
)


class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()


del click
