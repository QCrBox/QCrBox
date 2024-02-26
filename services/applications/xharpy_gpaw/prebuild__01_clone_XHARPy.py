import subprocess
from pathlib import Path

TARGET_DIR = Path(__file__).absolute().parent / "XHARPy"

# If target dir exists, update repo to the latest version. Otherwise, do a fresh clone to the target dir.
subprocess.call(
    f'git -C "{TARGET_DIR}" pull || git clone --depth 1 https://github.com/Niolon/XHARPy.git "{TARGET_DIR}"', shell=True
)

