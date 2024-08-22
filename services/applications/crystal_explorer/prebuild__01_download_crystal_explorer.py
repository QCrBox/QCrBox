#!/usr/bin/env python
import sys
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

import requests

from pyqcrbox.logging import logger


def calculate_hash(path):
    with open(path, "rb") as f:
        content = f.read()
    return sha256(content).hexdigest()


def verify_checksum(file_path, expected_hash):
    file_path = Path(file_path)

    computed_hash = calculate_hash(file_path)
    if computed_hash != expected_hash:
        logger.error(
            "The file had a hash that was different than the expected value. "
            f"Computed hash: {computed_hash!r}, expected hash: {expected_hash!r}"
        )
        sys.exit(1)


def download_file(url: str, target_dir: Path) -> Path:
    target_file = target_dir.joinpath(Path(urlparse(url).path).name)
    if target_file.exists():
        logger.debug(
            f"Target file {Path('shelx_executables').joinpath(target_file.name)} already exists. Not downloading again."
        )
        return target_file

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        msg = f"Could not download {url!r} (reason: {response.reason}). "
        logger.error(msg)
        sys.exit(1)

    logger.debug(f"Downloading file: {url} -> {Path('shelx_executables').joinpath(target_file.name)}")
    with open(target_file, mode="wb") as fp:
        for chunk in response.iter_content(chunk_size=16 * 1024):
            fp.write(chunk)

    return target_file


def download_crystal_explorer_ubuntu_package():
    url = "https://releases.crystalexplorer.net/CrystalExplorer-21.5-ubuntu-20.04.deb"
    expected_hash = "d01e20123084bf13750823577bcea82f93c28e3f47845de91800246a831ecdf1"

    here = Path(__file__).parent
    output_file = download_file(url, here)
    verify_checksum(output_file, expected_hash)


if __name__ == "__main__":
    download_crystal_explorer_ubuntu_package()
