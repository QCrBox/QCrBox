# SPDX-License-Identifier: MPL-2.0

import click
import doit.task

from ..helpers import NaturalOrderGroup, get_repo_root, run_tasks


@click.group(name="dev", cls=NaturalOrderGroup)
def dev_commands():
    """
    Development-related commands.
    """
    pass


@dev_commands.command(name="update-deps")
def update_dependency_versions():
    """
    Update dependencies in `pyqcrbox/requirements*.txt` to the latest available versions.
    """
    repo_root = get_repo_root()
    pyqcrbox_root = repo_root.joinpath("pyqcrbox")

    actions = [
        f"cd {pyqcrbox_root} && uv pip compile -U --output-file=requirements.txt pyproject.toml",
        f"cd {pyqcrbox_root} && uv pip compile -U --extra=dev --output-file=requirements-dev.txt pyproject.toml",
        f"cd {pyqcrbox_root} && uv pip compile -U --extra=docs --output-file=requirements-docs.txt pyproject.toml",
        f"cd {pyqcrbox_root} && uv pip compile -U --extra=server --output-file=requirements-server.txt pyproject.toml",
        f"cd {pyqcrbox_root} && uv pip compile -U --extra=client --output-file=requirements-client.txt pyproject.toml",
        f"cd {pyqcrbox_root} && uv pip compile -U --extra=all --output-file=requirements-all.txt pyproject.toml",
    ]

    task = doit.task.dict_to_task(
        {
            "name": "update-dependency-versions",
            "actions": actions,
        }
    )
    run_tasks([task])
