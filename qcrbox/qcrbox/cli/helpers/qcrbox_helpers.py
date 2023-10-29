import subprocess
from pathlib import Path
from typing import Optional, TypeVar

from git import Repo

# Type alias
PathLike = TypeVar("PathLike", str, Path)


def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    proc = subprocess.run(["hatch", "version"], cwd=Path(__file__).parent, capture_output=True)
    proc.check_returncode()
    return proc.stdout.strip().decode()


def get_repo_root(path: Optional[PathLike] = None):
    path = path or Path.cwd()
    repo = Repo(Path(path).resolve(), search_parent_directories=True)
    return Path(repo.working_tree_dir).resolve()
