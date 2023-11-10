import os
import pathlib
import re
import shutil
import subprocess
import textwrap

from typing import TypeVar

from .compose_file_config import ComposeFileConfig
from .qcrbox_helpers import get_repo_root, get_current_qcrbox_version
from ...logging import logger

# Type alias
PathLike = TypeVar("PathLike", str, pathlib.Path)


class QCrBoxSubprocessError(Exception):
    """
    Custom exception to indicate errors during the build process of QCrBox components.
    """


class DockerProject:
    def __init__(self, *, name: str = "qcrbox", compose_file_config: ComposeFileConfig = None):
        self.project_name = name
        self.compose_file_config = compose_file_config or ComposeFileConfig()
        self.repo_root = self.compose_file_config.repo_root

    def __repr__(self):
        clsname = self.__class__.__name__
        res = f"<{clsname}: {self.project_name!r}\n   repo_root: {self.repo_root}"
        for compose_file in self.compose_file_config.get_compose_files(relative_path=True):
            res += f"\n    - {compose_file}"
        res += "\n >"
        return res

    def print_list_of_components(self, print_func=print):
        for compose_file in self.compose_file_config.compose_files:
            print_func()
            print_func(f"Components defined in {compose_file.as_posix()!r}:")
            print_func()
            for service in self.get_services_for_compose_file(compose_file):
                print_func(f"   - {service}")

    @property
    def services(self):
        return self.services_excluding_base_images

    @property
    def services_including_base_images(self):
        return list(self.compose_file_config._full_service_metadata["services"].keys())

    @property
    def services_excluding_base_images(self):
        return [
            service_name
            for service_name in self.compose_file_config._full_service_metadata["services"].keys()
            if not service_name.startswith("base-")
        ]

    def get_services_for_compose_file(self, compose_file):
        compose_file_relative_path = compose_file.relative_to(self.repo_root)
        return list(self.compose_file_config._service_metadata_by_compose_file[compose_file_relative_path]["services"].keys())

    def _construct_docker_compose_command(self, cmd: str, *cmd_args: str):
        env_dev_file = self.repo_root.joinpath(".env.dev")

        cmd = (
            [
                shutil.which("docker"),
                "compose",
                f"--project-name={self.project_name}",
                f"--env-file={env_dev_file.as_posix()}",
            ]
            + [f"--file={compose_file.as_posix()}" for compose_file in self.compose_file_config.compose_files]
            + [cmd]
            + list(cmd_args)
        )

        return cmd

    def run_docker_compose_command(self, cmd: str, *cmd_args: str, dry_run: bool = False, capture_output: bool = False):
        full_cmd = self._construct_docker_compose_command(cmd, *cmd_args)
        logger.debug(f"Running docker compose command: {' '.join(full_cmd)!r}")

        custom_env = os.environ.copy()
        custom_env["QCRBOX_PYTHON_PACKAGE_VERSION"] = get_current_qcrbox_version()
        logger.debug(f"Current qcrbox version: {custom_env['QCRBOX_PYTHON_PACKAGE_VERSION']}")

        if not dry_run:
            proc = subprocess.run(full_cmd, env=custom_env, shell=False, check=False, capture_output=capture_output)
            try:
                proc.check_returncode()
            except subprocess.CalledProcessError as exc:
                cmd = " ".join(exc.cmd)
                captured_stdout = textwrap.indent(
                    f"\n\n{exc.stdout.decode()}\n" if exc.stdout else "(not captured)",
                    prefix=" " * 24,
                )
                captured_stderr = textwrap.indent(
                    f"\n\n{exc.stderr.decode()}\n" if exc.stderr else "(not captured)",
                    prefix=" " * 24,
                )
                msg = textwrap.dedent(
                    f"""\
                    An error occurred when executing the following command:

                        {cmd}

                    Return code: {exc.returncode}

                    Captured stdout: {captured_stdout}
                    Captured stderr: {captured_stderr}
                    """
                )
                raise QCrBoxSubprocessError(msg)
            return proc

    def build_single_docker_image(self, target_image: str, dry_run: bool = False, capture_output: bool = False):
        logger.info(f"Building docker image: {target_image}")
        self.run_docker_compose_command("build", target_image, dry_run=dry_run, capture_output=capture_output)

    def get_build_dependencies(self, service_name):
        dockerfile = self.compose_file_config.get_dockerfile_for_service(service_name)
        contents = dockerfile.open().readlines()
        dependency_lines = [line for line in contents if line.startswith("FROM qcrbox")]
        dependency_names = [
            re.match("^FROM qcrbox/(?P<image_name>.*):", line).group("image_name") for line in dependency_lines
        ]
        return dependency_names

    def get_runtime_dependencies(self, service_name):
        try:
            runtime_deps = self.compose_file_config._full_service_metadata["services"][service_name]["depends_on"]
        except KeyError:
            # no runtime dependencies
            runtime_deps = []

        if not isinstance(runtime_deps, list):
            assert isinstance(runtime_deps, dict)
            runtime_deps = list(runtime_deps.keys())

        return runtime_deps

    def get_build_and_runtime_dependencies(self, service_name):
        return self.get_build_dependencies(service_name) + self.get_runtime_dependencies(service_name)

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

    def _build_incl_dependencies(self, *target_images, capture_output: bool = False):
        for target_image in target_images:
            for service_name in self.get_dependency_chain(target_image):
                self.build_single_docker_image(service_name, capture_output=capture_output)

    def build_docker_images(self, *target_images, no_deps: bool = False, capture_output: bool = False):
        if no_deps:
            self.run_docker_compose_command("build", *target_images, capture_output=capture_output)
        else:
            self._build_incl_dependencies(*target_images, capture_output=capture_output)

    def spin_down_docker_containers(self, target_containers, dry_run: bool = False, capture_output: bool = False):
        if target_containers == ():
            logger.info(f"Stopping and removing all QCrBox docker containers ({', '.join(target_containers)}")
            self.run_docker_compose_command("down", dry_run=dry_run, capture_output=capture_output)

        else:
            for target_container in target_containers:
                target_container_incl_deps = [target_container] + list(self.get_dependency_chain(target_container))
                logger.info(
                    f"Stopping and removing the following QCrBox docker containers: {target_container_incl_deps}"
                )
                self.run_docker_compose_command(
                    "rm",
                    "--stop",
                    "--force",
                    *target_container_incl_deps,
                    dry_run=dry_run,
                    capture_output=capture_output,
                )

    def get_service_status(self, service_name):
        logger.warning("TODO: finish the implementation of 'get_status_of_docker_service'")
        raise NotImplementedError("TODO: finish the implementation")
