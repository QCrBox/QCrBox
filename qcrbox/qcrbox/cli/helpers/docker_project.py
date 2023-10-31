import os
import pathlib
import shutil
import subprocess
import sys

import yaml
from pathlib import Path

from git.exc import InvalidGitRepositoryError
from pydantic.v1.utils import deep_update
from typing import TypeVar

from .qcrbox_helpers import get_repo_root, get_current_qcrbox_version
from ..logging import logger

# Type alias
PathLike = TypeVar("PathLike", str, pathlib.Path)


def load_docker_compose_data(*compose_files: PathLike):
    docker_compose_data = {}
    for compose_file in compose_files:
        docker_compose_data = deep_update(docker_compose_data, yaml.safe_load(Path(compose_file).open()))
    return docker_compose_data


class DockerProject:
    def __init__(self, name: str, *compose_files: PathLike):
        self.project_name = name
        self.repo_root = self._find_common_repo_root(*compose_files)
        self.compose_files = [Path(compose_file).resolve() for compose_file in compose_files]

        self._service_metadata_by_compose_file = {
            compose_file.relative_to(self.repo_root): load_docker_compose_data(compose_file)
            for compose_file in self.compose_files
        }
        self._full_service_metadata = {}
        for compose_file, data in self._service_metadata_by_compose_file.items():
            self._full_service_metadata = deep_update(self._full_service_metadata, data)

    def __repr__(self):
        clsname = self.__class__.__name__
        res = f"<{clsname}: {self.project_name!r}\n   repo_root: {self.repo_root}"
        for compose_file in self.compose_files:
            res += f"\n    - {compose_file.relative_to(self.repo_root)}"
        res += "\n >"
        return res

    def _find_common_repo_root(self, *compose_files: PathLike):
        if compose_files == ():
            raise ValueError("No compose file specified.")

        try:
            repo_candidates = set(get_repo_root(compose_file) for compose_file in compose_files)
        except InvalidGitRepositoryError:
            raise ValueError("Unable to determine root repository of the given compose files.")

        if len(repo_candidates) > 1:
            raise ValueError("All specified compose files must live in the same repository.")

        return repo_candidates.pop()

    @property
    def services(self):
        return list(self._full_service_metadata["services"].keys())

    def _construct_docker_compose_command(self, cmd: str, *cmd_args: str):
        env_dev_file = self.repo_root.joinpath(".env.dev")

        cmd = (
            [
                shutil.which("docker"),
                "compose",
                f"--project-name={self.project_name}",
                f"--env-file={env_dev_file.as_posix()}",
            ]
            + [f"--file={compose_file.as_posix()}" for compose_file in self.compose_files]
            + [cmd]
            + list(cmd_args)
        )

        return cmd

    def run_docker_compose_command(self, cmd: str, *cmd_args: str, capture_output: bool = False, dry_run: bool = False):
        full_cmd = self._construct_docker_compose_command(cmd, *cmd_args)
        logger.debug(f"Running docker compose command: {' '.join(full_cmd)!r}")

        custom_env = os.environ.copy()
        custom_env["QCRBOX_PYTHON_PACKAGE_VERSION"] = get_current_qcrbox_version()
        logger.debug(f"Current qcrbox version: {custom_env['QCRBOX_PYTHON_PACKAGE_VERSION']}")

        if not dry_run:
            proc = subprocess.run(full_cmd, env=custom_env, shell=False, check=False, capture_output=capture_output)
            return proc

    def build_single_docker_image(self, target_image: str, dry_run: bool, capture_output: bool = False):
        logger.info(f"Building docker image: {target_image}")
        self.run_docker_compose_command("build", target_image, dry_run=dry_run, capture_output=capture_output)
