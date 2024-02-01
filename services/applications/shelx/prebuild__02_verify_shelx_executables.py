#!/usr/bin/env python

from hashlib import sha256
from pathlib import Path


class WrongHashException(Exception):
    pass


def load_sha256_checksums():
    hashes = {}
    with open("shelx_checksums.txt", "r", encoding="UTF-8") as f:
        for hash_line in f.readlines():
            if hash_line.startswith("#") or hash_line.strip() == "":
                continue
            hash_value, executable = hash_line.split()
            hashes[Path(executable)] = hash_value

    return hashes


def calculate_hash(path):
    with open(path, "rb") as f:
        content = f.read()
    return sha256(content).hexdigest()


def verify_checksums():
    here = Path(__file__).parent

    hashes = load_sha256_checksums()
    failed_comparisons = []
    for path, correct_hash in hashes.items():
        computed_hash = calculate_hash(here.joinpath(path))
        if computed_hash != correct_hash:
            failed_comparisons.append(path)
            print(correct_hash, computed_hash)
    if len(failed_comparisons) > 0:
        wrong_files_str = ", ".join(str(path) for path in failed_comparisons)
        raise WrongHashException(
            "The following files had a hash that was different than the expected "
            f"value from shelx.checksums.txt: {wrong_files_str}"
        )


if __name__ == "__main__":
    verify_checksums()
