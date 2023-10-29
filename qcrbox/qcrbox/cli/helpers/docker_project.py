import pathlib
import yaml
from pathlib import Path

from git.exc import InvalidGitRepositoryError
from pydantic.v1.utils import deep_update
from typing import TypeVar

from .qcrbox_helpers import get_repo_root

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

        self.data_by_compose_file = {
            compose_file.relative_to(self.repo_root): load_docker_compose_data(compose_file)
            for compose_file in self.compose_files
        }
        self.full_data = {}
        for compose_file, data in self.data_by_compose_file.items():
            self.full_data = deep_update(self.full_data, data)

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
        return list(self.full_data["services"].keys())
