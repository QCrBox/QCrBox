import shutil
import time
from pathlib import Path


def print_cif(input_cif: str, print_times: int):
    """A short running command which prints the input_cif and returns it back."""

    for _ in range(print_times):
        print(input_cif)

    return input_cif


def infinite_loop(dummy: str):
    """A command which runs forever and takes no parameters."""

    count = 0

    while True:
        count += 1
        print(f"{count = }")
        time.sleep(2)


def change_cif_name(input_cif: str, output_cif_name: str):
    """Change the name of the output CIF."""

    input_cif_path = Path(input_cif)
    output_cif_path = input_cif_path.parent / output_cif_name
    output_cif_path = output_cif_path.with_suffix(".cif")
    shutil.copy(input_cif_path, output_cif_path)

    return output_cif_path


def print_two_cif(cif1: str, cif2: str):
    """A command to print the contents of cif1 and cif2."""

    def _print(fp):
        print(fp)
        with open(fp, "r") as file:
            print(file.readlines())

    _print(cif1)
    _print(cif2)

    return cif2
