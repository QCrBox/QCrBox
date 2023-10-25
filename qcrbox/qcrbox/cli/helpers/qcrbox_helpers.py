import subprocess
from pathlib import Path


def get_current_qcrbox_version() -> str:
    """
    Return the current version of the 'qcrbox' module.
    """
    proc = subprocess.run(["hatch", "version"], cwd=Path(__file__).parent, capture_output=True)
    proc.check_returncode()
    return proc.stdout.strip().decode()
