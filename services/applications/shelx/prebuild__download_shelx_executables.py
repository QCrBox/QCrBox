#!/usr/bin/env python

import os
from pathlib import Path
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


def download_executable(url, target_dir):
    username = os.environ["QCRBOX_SHELX_DOWNLOAD_USERNAME"]
    password = os.environ["QCRBOX_SHELX_DOWNLOAD_PASSWORD"]

    r = urlparse(url)
    target_file = target_dir.joinpath(Path(r.path).name)

    response = requests.get(url, stream=True, auth=HTTPBasicAuth(username, password))
    with open(target_file, mode="wb") as f:
        logger.debug(f"Downloading file: {target_file.name}")
        for chunk in response.iter_content(chunk_size=10 * 1024):
            f.write(chunk)


def find_missing_executables():
    pass


def download_shelx_executables():
    here = Path(__file__).parent
    target_dir = here.joinpath("shelx_executables")
    for url in load_shelx_executable_urls():
        download_executable(url, target_dir)


if __name__ == "__main__":
    download_shelx_executables()
