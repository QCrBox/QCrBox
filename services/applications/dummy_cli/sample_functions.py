import time


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
