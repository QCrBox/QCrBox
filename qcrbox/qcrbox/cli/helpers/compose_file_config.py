# SPDX-License-Identifier: MPL-2.0

import re
import sys
from pathlib import Path

import click
import yaml
from pydantic.v1.utils import deep_update

from .qcrbox_helpers import PathLike, find_common_repo_root, get_repo_root


def load_docker_compose_data(*compose_files: PathLike):
    docker_compose_data = {}
    for compose_file in compose_files:
        with Path(compose_file).open() as f:
            docker_compose_data = deep_update(docker_compose_data, yaml.safe_load(f))
    return docker_compose_data


class ComposeFileConfig:
    def __init__(self, *, compose_files_build=None, compose_files_runtime=None):
        compose_files_build = compose_files_build or ()
        compose_files_runtime = compose_files_runtime or ()

        if compose_files_build == () and compose_files_runtime == ():
            raise ValueError("Arguments `compose_files_build` and `compose_files_runtime` cannot both be empty.")

        self.repo_root = find_common_repo_root(*compose_files_build, *compose_files_runtime)
        self.compose_files_build = [Path(compose_file).resolve() for compose_file in compose_files_build]
        self.compose_files_runtime = [Path(compose_file).resolve() for compose_file in compose_files_runtime]

        self._service_metadata_by_compose_file = {
            compose_file.relative_to(self.repo_root): load_docker_compose_data(compose_file)
            for compose_file in self.compose_files_build + self.compose_files_runtime
        }
        self._full_service_metadata = {}
        for compose_file, data in self._service_metadata_by_compose_file.items():
            self._full_service_metadata = deep_update(self._full_service_metadata, data)

    @classmethod
    def get_default_config(cls):
        repo_root = get_repo_root()
        compose_files_build = [repo_root.joinpath("docker-compose.build.yml")]
        compose_files_runtime = [repo_root.joinpath("docker-compose.yml")]
        return cls(compose_files_build=compose_files_build, compose_files_runtime=compose_files_runtime)

    @classmethod
    def get_config(cls, config_name):
        match config_name:
            case "default":
                return cls.get_default_config()
            case _:
                raise ValueError(f"Invalid config name: {config_name}")

    @property
    def services_including_base_images(self):
        return list(self._full_service_metadata["services"].keys())

    @property
    def services_excluding_base_images(self):
        return [
            service_name
            for service_name in self._full_service_metadata["services"]
            if not service_name.startswith("base-")
        ]

    def get_build_context(self, service_name):
        try:
            return self._full_service_metadata["services"][service_name]["build"]["context"]
        except KeyError:
            click.echo(f"Invalid component name: {service_name!r}")
            click.echo()
            click.echo("Run 'qcb list components' to get a list of valid component names.")
            sys.exit(1)

    def get_dockerfile_for_service(self, service_name):
        build_context = self.get_build_context(service_name)
        return self.repo_root.joinpath(build_context).joinpath("Dockerfile")

    def get_build_dependencies(self, service_name):
        dockerfile = self.get_dockerfile_for_service(service_name)
        contents = dockerfile.open().readlines()
        dependency_lines = [line for line in contents if line.startswith("FROM qcrbox")]
        dependency_names = [
            re.match("^FROM qcrbox/(?P<image_name>.*):", line).group("image_name") for line in dependency_lines
        ]
        return dependency_names

    def get_runtime_dependencies(self, service_name):
        try:
            runtime_deps = self._full_service_metadata["services"][service_name]["depends_on"]
        except KeyError:
            # no runtime dependencies
            runtime_deps = []

        if not isinstance(runtime_deps, list):
            assert isinstance(runtime_deps, dict)
            runtime_deps = list(runtime_deps.keys())

        return runtime_deps

    def get_build_and_runtime_dependencies(self, service_name):
        return self.get_build_dependencies(service_name) + self.get_runtime_dependencies(service_name)

    def get_direct_dependencies(self, service_name: str, include_build_deps: bool = False):
        if include_build_deps:
            return self.get_build_and_runtime_dependencies(service_name)
        else:
            return self.get_runtime_dependencies(service_name)

    def get_dependency_chain(self, service_name, include_build_deps=False):
        deps_done = []
        deps_todo = [service_name]

        def tidy_up_deps(deps_done, deps_todo):
            return list({x: None for x in deps_todo if x not in deps_done}.keys())

        while deps_todo:
            cur_dep = deps_todo.pop(0)
            deps_done.append(cur_dep)
            if include_build_deps:
                deps_todo += self.get_build_and_runtime_dependencies(cur_dep)
            else:
                deps_todo += self.get_runtime_dependencies(cur_dep)
            deps_todo = tidy_up_deps(deps_done, deps_todo)

        # Remove the parent service name to avoid circular dependencies
        deps_done.remove(service_name)

        return reversed(deps_done)

    @property
    def compose_files(self):
        return self.compose_files_build + self.compose_files_runtime

    @property
    def command_line_options(self):
        return [f"--file={compose_file}" for compose_file in self.compose_files]
