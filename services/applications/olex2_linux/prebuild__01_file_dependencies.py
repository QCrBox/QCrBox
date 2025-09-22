import pathlib

import requests
from pyqcrbox import logger

url_zip = "https://secure.olex2.org/olex2-distro/1.5-alpha/olex2-linux64.zip"
output_path = pathlib.Path("olex2_files/olex2-linux64.zip")


def create_new_olex2_zip_file():
    logger.debug(f"Downloading Olex2 archive from: {url_zip}")
    r = requests.get(url_zip, timeout=600)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as fobj:
        fobj.write(r.content)


if __name__ == "__main__":
    if not output_path.exists():
        create_new_olex2_zip_file()
