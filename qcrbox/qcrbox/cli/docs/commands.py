import click
import doit.task

from ..helpers import run_tasks


@click.group(name="docs")
def docs_group():
    """
    Build or serve the documentation.
    """
    pass


@docs_group.command()
def build():
    """
    Build the documentation.
    """
    task = doit.task.dict_to_task(
        {
            "name": "build-docs",
            "actions": ["mkdocs build"],
        }
    )
    run_tasks([task])
