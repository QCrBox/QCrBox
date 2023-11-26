#!/usr/bin/env bash

set -euo pipefail

if ! [ -e ./shelx_checksums.txt ]; then
    echo "Current working directory: $(pwd)"
    echo "Could not find checksum file: './shelx_checksums.txt"
    exit 1
fi

if sha256sum --check ./shelx_checksums.txt; then
    echo ""
    echo "Successfully verified checksums for SHELX all executables"
else
    echo ""
    echo "Error: at least one SHELX executable is missing or does not have the expected SHA-256 checksum"
    echo "Please place the correct executables in the 'shelx_executables' subfolder. You can download them"
    echo "from the SHELX website: https://shelx.uni-goettingen.de/download.php"
    exit 1
fi
