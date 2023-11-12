import functools
import subprocess
from pathlib import Path
from typing import Optional, TypeVar

from git import Repo

# Type alias
PathLike = TypeVar("PathLike", str, Path)

__all__ = ["get_current_qcrbox_version", "get_repo_root", "get_qcrbox_api_base_url"]


@functools.lru_cache(maxsize=1)
def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    proc = subprocess.run(["hatch", "--no-color", "version"], cwd=Path(__file__).parent, capture_output=True)
    proc.check_returncode()
    return proc.stdout.strip().decode()


def get_repo_root(path: Optional[PathLike] = None):
    path = path or Path.cwd()
    repo = Repo(Path(path).resolve(), search_parent_directories=True)
    return Path(repo.working_tree_dir).resolve()


def get_qcrbox_api_base_url():
    # FIXME: derive the API URL from global configuration options and/or command line arguments
    return "http://127.0.0.1:11000"
