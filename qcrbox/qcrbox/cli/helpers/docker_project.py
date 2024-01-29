# SPDX-License-Identifier: MPL-2.0

import os
import subprocess
import textwrap

from loguru import logger

from .compose_file_config import ComposeFileConfig
from .qcrbox_helpers import get_current_qcrbox_version

__all__ = ["DockerProject"]


class QCrBoxSubprocessError(Exception):
    """
    Custom exception to indicate errors during the build process of QCrBox components.
    """


def prettyprint_called_process_error(exc: subprocess.CalledProcessError):
    cmd = " ".join(exc.cmd)
    prefix = " " * 24
    captured_stdout = textwrap.indent(f"\n\n{exc.stdout.decode()}\n" if exc.stdout else "(not captured)", prefix=prefix)
    captured_stderr = textwrap.indent(f"\n\n{exc.stderr.decode()}\n" if exc.stderr else "(not captured)", prefix=prefix)
    msg = textwrap.dedent(
        f"""\
        An error occurred when executing the following command:

            {cmd}

        Return code: {exc.returncode}

        Captured stdout: {captured_stdout}
        Captured stderr: {captured_stderr}
        """
    )
    return msg


class DockerProject:
    def __init__(self, *, name: str = "qcrbox", config_name: str = "default"):
        self.project_name = name
        self.compose_file_config = ComposeFileConfig.get_config(config_name)
        self.repo_root = self.compose_file_config.repo_root

    @property
    def services_including_base_images(self):
        return self.compose_file_config.services_including_base_images

    @property
    def services_excluding_base_images(self):
        return self.compose_file_config.services_excluding_base_images

    def get_build_context(self, service_name):
        return self.compose_file_config.get_build_context(service_name)

    def get_direct_dependencies(self, service_name: str, include_build_deps: bool = False):
        return self.compose_file_config.get_direct_dependencies(service_name, include_build_deps=include_build_deps)

    def get_dependency_chain(self, service_name, include_build_deps=False):
        return self.compose_file_config.get_dependency_chain(service_name, include_build_deps=include_build_deps)

    def build_single_docker_image(self, target_image: str, dry_run: bool = False, capture_output: bool = False):
        logger.info(f"Building docker image: {target_image}", dry_run=dry_run)
        self.run_docker_compose_command("build", target_image, dry_run=dry_run, capture_output=capture_output)

    def _construct_docker_compose_command(self, cmd: str, *cmd_args: str):
        env_dev_file = self.repo_root.joinpath(".env.dev")

        cmd = (
            [
                "docker",
                "compose",
                f"--project-name={self.project_name}",
                f"--env-file={env_dev_file.as_posix()}",
            ]
            + self.compose_file_config.command_line_options
            + [cmd]
            + list(cmd_args)
        )

        return cmd

    def run_docker_compose_command(self, cmd: str, *cmd_args: str, dry_run: bool = False, capture_output: bool = False):
        full_cmd = self._construct_docker_compose_command(cmd, *cmd_args)
        logger.debug(f"Running docker compose command: {' '.join(full_cmd)!r}", dry_run=dry_run)

        custom_env = os.environ.copy()
        custom_env["QCRBOX_PYTHON_PACKAGE_VERSION"] = get_current_qcrbox_version()
        custom_env["QCRBOX_SHARED_FILES_DIR_HOST_PATH"] = str(self.repo_root.joinpath("shared_files"))
        logger.debug(f"Current qcrbox version: {custom_env['QCRBOX_PYTHON_PACKAGE_VERSION']}", dry_run=dry_run)

        if not dry_run:
            proc = subprocess.run(full_cmd, env=custom_env, shell=False, check=False, capture_output=capture_output)
            try:
                proc.check_returncode()
            except subprocess.CalledProcessError as exc:
                error_msg = prettyprint_called_process_error(exc)
                raise QCrBoxSubprocessError(error_msg)
            return proc

    def start_up_docker_containers(self, target_containers: list[str], dry_run):
        logger.info(f"Starting up docker container(s): {', '.join(target_containers)}", dry_run=dry_run)
        if not dry_run:
            self.run_docker_compose_command("up", "-d", *target_containers, dry_run=dry_run)

    def spin_down_docker_containers(self, target_containers, dry_run: bool = False, capture_output: bool = False):
        if target_containers == ():
            msg = f"Stopping and removing all QCrBox docker containers ({', '.join(target_containers)}"
            logger.info(msg, dry_run=dry_run)
            self.run_docker_compose_command("down", dry_run=dry_run, capture_output=capture_output)

        else:
            for target_container in target_containers:
                target_container_incl_deps = [target_container] + list(self.get_dependency_chain(target_container))
                msg = f"Stopping and removing the following QCrBox docker containers: {target_container_incl_deps}"
                logger.info(msg, dry_run=dry_run)
                self.run_docker_compose_command(
                    "rm",
                    "--stop",
                    "--force",
                    *target_container_incl_deps,
                    dry_run=dry_run,
                    capture_output=capture_output,
                )
