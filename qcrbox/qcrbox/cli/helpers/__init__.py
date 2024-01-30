# SPDX-License-Identifier: MPL-2.0

import click

from .docker_project import DockerProject
from .doit_helpers import make_task, run_tasks
from .qcrbox_helpers import get_qcrbox_whl_output_path, get_repo_root


class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()


del click
