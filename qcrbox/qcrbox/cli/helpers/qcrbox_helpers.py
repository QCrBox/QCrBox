import functools
import os
import subprocess
from pathlib import Path
from typing import Optional, TypeVar

from git import Repo

# Type alias
PathLike = TypeVar("PathLike", str, Path)


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


def get_rabbitmq_connection_url(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
):
    host = host or os.environ.get("QCRBOX_HOST_RABBITMQ", "127.0.0.1")
    port = port or int(os.environ.get("QCRBOX_PORT_RABBITMQ", 5672))
    username = username or os.environ.get("QCRBOX_RABBITMQ_USERNAME", "guest")
    password = password or os.environ.get("QCRBOX_RABBITMQ_PASSWORD", "guest")
    url = f"amqp://{username}:{password}@{host}:{port}/"
    return url
