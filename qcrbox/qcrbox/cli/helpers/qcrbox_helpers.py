import subprocess
from pathlib import Path

from git import Repo


def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    proc = subprocess.run(["hatch", "version"], cwd=Path(__file__).parent, capture_output=True)
    proc.check_returncode()
    return proc.stdout.strip().decode()


def get_repo_root():
    repo = Repo(".", search_parent_directories=True)
    return Path(repo.working_tree_dir).resolve()
