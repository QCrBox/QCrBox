#!/usr/bin/env python
import bz2
import os
import sys
from pathlib import Path
from time import sleep
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth

from qcrbox.logging import logger


def load_shelx_executable_urls():
    here = Path(__file__).parent
    with open(here.joinpath("shelx_download_urls.txt")) as f:
        urls = f.readlines()
    urls = [url.strip() for url in urls if url.strip() != ""]
    return urls


class NoDecompressor:
    def decompress(self, chunk):
        return chunk


def download_executable(url, target_dir):
    target_file = target_dir.joinpath(Path(urlparse(url).path).name)
    if target_file.exists():
        logger.debug(
            f"Target file {Path('shelx_executables').joinpath(target_file.name)} already exists. Not downloading again."
        )
        return

    username = os.environ["QCRBOX_SHELX_DOWNLOAD_USERNAME"]
    password = os.environ["QCRBOX_SHELX_DOWNLOAD_PASSWORD"]

    response = requests.get(url, stream=True, auth=HTTPBasicAuth(username, password))
    if response.status_code != 200:
        msg = f"Could not download {url!r} (reason: {response.reason}). "
        if response.status_code == 401:
            msg += (
                "Please make sure that the environment variables QCRBOX_SHELX_DOWNLOAD_USERNAME "
                "and QCRBOX_SHELX_DOWNLOAD_PASSWORD are set to the correct values."
            )
        logger.error(msg)
        sys.exit(1)

    if target_file.suffix == ".bz2":
        decompressor = bz2.BZ2Decompressor()
        target_file = target_file.with_suffix("")  # strip the.bz2 extension
    else:
        decompressor = NoDecompressor()

    logger.debug(f"Downloading file: {url} -> {Path('shelx_executables').joinpath(target_file.name)}")
    with open(target_file, mode="wb") as fp:
        for chunk in response.iter_content(chunk_size=16 * 1024):
            fp.write(decompressor.decompress(chunk))


def find_missing_executables():
    pass


def download_shelx_executables():
    here = Path(__file__).parent
    target_dir = here.joinpath("shelx_executables")
    for url in load_shelx_executable_urls():
        download_executable(url, target_dir)
        sleep(1.0)  # apply rate limiting to avoid 'max retries exceeded' error


if __name__ == "__main__":
    download_shelx_executables()
