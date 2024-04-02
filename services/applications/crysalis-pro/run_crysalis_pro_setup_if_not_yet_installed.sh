#!/usr/bin/env bash

set -Eeuo pipefail

if ! [[ -d "${WINEPREFIX}" ]]; then
    echo "Error: directory WINEPREFIX='${WINEPREFIX}' does not exist."
    echo "Aborting because it looks like something went wrong with the Wine setup."
    exit 1
fi

if [[ "${WINEARCH}" != "win64" ]]; then
    echo "Error: environment variable WINEARCH must have value 'win64', but it is set to '${WINEARCH}'."
    exit 2
fi

EXISTING_CRYSALIS_PRO_EXECUTABLE=$(find ${WINEPREFIX}/drive_c/Xcalibur/CrysAlisPro* -name pro.exe -print -quit || true)
if [[ -n "${EXISTING_CRYSALIS_PRO_EXECUTABLE}" ]]; then
    echo "CrysAlisPro is already installed. No need to run setup script again."
    exit 0
fi

# Run CrysAlis Pro installer in silent mode
wine ${QCRBOX_ROOT_DIR}/CrysAlisPro171.43.48a.exe /S /v/qn

echo "Done."
