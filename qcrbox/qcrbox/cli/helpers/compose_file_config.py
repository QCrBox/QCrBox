import pathlib
import yaml
from pathlib import Path
from pydantic.utils import deep_update
from typing import TypeVar

from git import InvalidGitRepositoryError

from .qcrbox_helpers import get_repo_root

# Type alias
PathLike = TypeVar("PathLike", str, pathlib.Path)


def load_docker_compose_data(*compose_files: PathLike):
    docker_compose_data = {}
    for compose_file in compose_files:
        docker_compose_data = deep_update(docker_compose_data, yaml.safe_load(Path(compose_file).open()))
    return docker_compose_data


class ComposeFileConfig:
    def __init__(self, *, compose_files_build=None, compose_files_runtime=None):
        compose_files_build = compose_files_build or ()
        compose_files_runtime = compose_files_runtime or ()

        self.repo_root = self._find_common_repo_root(*compose_files_build, *compose_files_runtime)

        if compose_files_build == () and compose_files_runtime == ():
            # Use default compose files in this repository
            compose_files_build = [
                self.repo_root.joinpath("docker-compose.build.yml"),
            ]
            compose_files_runtime = [
                self.repo_root.joinpath("docker-compose.yml"),
            ]

        self.compose_files_build = [Path(compose_file).resolve() for compose_file in compose_files_build]
        self.compose_files_runtime = [Path(compose_file).resolve() for compose_file in compose_files_runtime]

        self._service_metadata_by_compose_file = {
            compose_file.relative_to(self.repo_root): load_docker_compose_data(compose_file)
            for compose_file in self.compose_files_build + self.compose_files_runtime
        }
        self._full_service_metadata = {}
        for compose_file, data in self._service_metadata_by_compose_file.items():
            self._full_service_metadata = deep_update(self._full_service_metadata, data)

    def _find_common_repo_root(self, *compose_files: PathLike):
        # If no compose files are given, assume we're being called from
        # within a cloned qcrbox repo and look for its root folder.
        compose_files = compose_files or [__file__]

        try:
            repo_root_candidates = set(get_repo_root(compose_file) for compose_file in compose_files)
        except InvalidGitRepositoryError:
            raise ValueError("Unable to determine root repository of the given compose files.")

        if len(repo_root_candidates) > 1:
            raise ValueError("All specified compose files must live in the same repository.")

        return repo_root_candidates.pop()

    @property
    def compose_files(self):
        return self.compose_files_build + self.compose_files_runtime

    def get_compose_files(self, relative_path=False):
        if relative_path:
            return [compose_file.relative_to(self.repo_root) for compose_file in self.compose_files]
        else:
            return self.compose_files

    def get_dockerfile_for_service(self, service_name):
        return self.repo_root.joinpath(
            self._full_service_metadata["services"][service_name]["build"]["context"]
        ).joinpath("Dockerfile")
