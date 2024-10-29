# SPDX-License-Identifier: MPL-2.0

import subprocess
import textwrap
from pathlib import Path
from typing import Optional, TypeVar

import setuptools_scm
from git import InvalidGitRepositoryError, Repo

# Type alias
PathLike = TypeVar("PathLike", str, Path)

__all__ = ["get_current_pyqcrbox_version", "get_repo_root"]


def get_current_pyqcrbox_version() -> str:
    """
    Return the current version of the 'pyqcrbox' module.
    """
    return setuptools_scm.get_version(root=get_repo_root())


def get_repo_root(path: Optional[PathLike] = None):
    candidate_path = path or Path.cwd()

    try:
        repo = Repo(Path(candidate_path).resolve(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        if path is not None:
            raise ValueError(f"Unable to determine parent git repository of the given compose file: {path}")
        else:
            raise RuntimeError(
                "This command must be run from within a QCrBox git repository. "
                f"Current working directory: {candidate_path}"
            )
    return Path(repo.working_tree_dir).resolve()


def find_common_repo_root(*files: PathLike):
    files = files or [__file__]

    try:
        repo_root_candidates = set(get_repo_root(file) for file in files)
    except InvalidGitRepositoryError:
        raise ValueError("Unable to determine root repository of the given compose files.")

    if len(repo_root_candidates) > 1:
        raise ValueError("All specified files must live in the same repository.")

    return repo_root_candidates.pop()


def get_mkdocs_config_file_path():
    return get_repo_root().joinpath("mkdocs.yml")


class QCrBoxSubprocessError(Exception):
    """
    Custom exception to indicate errors during the build process of QCrBox components.
    """


def prettyprint_called_process_error(exc: subprocess.CalledProcessError):
    cmd = " ".join(exc.cmd)
    prefix = " " * 24
    captured_stdout = textwrap.indent(f"\n\n{exc.stdout.decode()}\n" if exc.stdout else "(no output)", prefix=prefix)
    captured_stderr = textwrap.indent(f"\n\n{exc.stderr.decode()}\n" if exc.stderr else "(no output)", prefix=prefix)
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
