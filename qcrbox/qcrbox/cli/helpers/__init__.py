import click

from .doit_helpers import make_task, run_tasks
from .docker_project import DockerProject
from .qcrbox_helpers import get_repo_root


class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()


del click
