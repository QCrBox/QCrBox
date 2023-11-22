import functools
import subprocess
from pathlib import Path
from typing import Optional, TypeVar

from git import Repo, InvalidGitRepositoryError

# Type alias
PathLike = TypeVar("PathLike", str, Path)

__all__ = ["get_current_qcrbox_version", "get_repo_root"]


@functools.lru_cache(maxsize=1)
def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    proc = subprocess.run(["hatch", "--no-color", "version"], cwd=Path(__file__).parent, capture_output=True)
    proc.check_returncode()
    return proc.stdout.strip().decode()


def get_repo_root(path: Optional[PathLike] = None):
    path = path or Path(__file__)
    repo = Repo(Path(path).resolve(), search_parent_directories=True)
    return Path(repo.working_tree_dir).resolve()


def find_common_repo_root(self, *files: PathLike):
    files = files or [__file__]

    try:
        repo_root_candidates = set(get_repo_root(file) for file in files)
    except InvalidGitRepositoryError:
        raise ValueError("Unable to determine root repository of the given compose files.")

    if len(repo_root_candidates) > 1:
        raise ValueError("All specified files must live in the same repository.")

    return repo_root_candidates.pop()
