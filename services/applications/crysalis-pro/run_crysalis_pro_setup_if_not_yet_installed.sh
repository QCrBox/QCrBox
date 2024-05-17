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

NEW_CRYSALIS_PRO_INSTALLER=$(find ${QCRBOX_ROOT_DIR}/CrysAlisPro* -name CrysAlisPro*.exe -print -quit)

# we still need a display for vcrun2015 to install properly
Xvfb :99 &
export DISPLAY=:99

# Run CrysAlis Pro installer in silent mode
wine ${NEW_CRYSALIS_PRO_INSTALLER} /S /v/qn

unset DISPLAY
echo "CrysAlis Pro setup script finished. Killing Xvfb..."
killall Xvfb

NEW_CRYSALIS_PRO_EXECUTABLE=$(find ${WINEPREFIX}/drive_c/Xcalibur/CrysAlisPro* -name pro.exe -print -quit || true)

cat << EOF > ./.idesktop/crysalispro.lnk
table Icon
  Caption: CrysAlisPro
  Command: wine ${NEW_CRYSALIS_PRO_EXECUTABLE}
  Icon: /opt/qcrbox/.idesktop/rigaku_oxford_diffraction_logo.png
  Width: 48
  Height: 48
  X: 70
  Y: 50
end
EOF
echo "Done."
