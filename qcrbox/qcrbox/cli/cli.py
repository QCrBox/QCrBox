import click

from .build.commands import build
from .docs.commands import docs_group
from .info.commands import show_info
from .up.commands import start_up_docker_containers
from .down.commands import shut_down_docker_containers


@click.group()
def entry_point():
    """
    Command line interface for the Quantum Crystallography Toolbox.
    """
    pass


entry_point.add_command(docs_group)
entry_point.add_command(build)
entry_point.add_command(show_info)
entry_point.add_command(start_up_docker_containers)
entry_point.add_command(shut_down_docker_containers)
