# SPDX-License-Identifier: MPL-2.0

import functools
import subprocess
from pathlib import Path
from typing import Optional, TypeVar

import click
from git import InvalidGitRepositoryError, Repo

from qcrbox.logging import set_cli_log_level

# Type alias
PathLike = TypeVar("PathLike", str, Path)

__all__ = ["get_current_qcrbox_version", "get_repo_root"]


@functools.lru_cache(maxsize=1)
def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    repo_root = get_repo_root()
    proc = subprocess.run(
        ["hatch", "--no-color", "version"],
        cwd=repo_root.joinpath("qcrbox"),
        capture_output=True,
    )
    proc.check_returncode()
    return proc.stdout.strip().decode()


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


def add_verbose_option(f):
    @functools.wraps(f)
    def wrapper(ctx, verbose, *args, **kwargs):
        ctx.ensure_object(dict)  # ensure that ctx.obj exists and is a dict
        ctx.obj["VERBOSE"] = verbose or ctx.obj.get("VERBOSE", False)
        if ctx.obj["VERBOSE"]:
            set_cli_log_level("DEBUG")
        return f(*args, **kwargs)

    wrapper = click.option(
        "-v",
        "--verbose",
        is_flag=True,
        default=None,
        help="Enables verbose mode (will print debugging messages about actions performed). [default: False]",
    )(wrapper)
    wrapper = click.pass_context(wrapper)

    return wrapper


def add_cli_option_enable_disable_components(f):
    DEFAULT_EXPLICITLY_ENABLED_COMPONENTS = ()
    DEFAULT_EXPLICITLY_DISABLED_COMPONENTS = ("shelx", "qcrbox-nextflow")

    f = click.option(
        "--disable",
        "disabled_components",
        default=DEFAULT_EXPLICITLY_DISABLED_COMPONENTS,
        show_default=True,
        metavar="COMPONENT",
        help="Explicitly exclude the given component from the build.",
        multiple=True,
    )(f)

    f = click.option(
        "--enable",
        "enabled_components",
        default=DEFAULT_EXPLICITLY_ENABLED_COMPONENTS,
        show_default=True,
        metavar="COMPONENT",
        help=(
            "Explicitly include the given component in the build. This only "
            "has an effect for components that are disabled by default."
        ),
        multiple=True,
    )(f)

    f = click.option(
        "--all",
        "include_all_components",
        default=False,
        show_default=True,
        is_flag=True,
        help=(
            "Include all components. Note that any components that are disabled by default"
            "or explicitly disabled (via --disable=COMPONENT) will remain excluded."
        ),
    )(f)

    return f
