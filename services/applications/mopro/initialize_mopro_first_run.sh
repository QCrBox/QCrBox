#!/usr/bin/env bash
#
# Build-time first-run initialization for MoProGUI.
#
# MoProGUI writes its roaming profile (mopro.ini) on first launch, which needs
# a running X display. Containers are spawned on demand per user, so this must
# happen once at image build time (under Xvfb) rather than at every container
# start. Mirrors the crysalis-pro build-time setup pattern.

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

if [[ -f "${MOPRO_ROAMING_PROFILE_DIR}/mopro.ini" ]]; then
    echo "MoPro roaming profile already exists. No need to run first-run initialization again."
    exit 0
fi

# An explicit screen size/depth matters: Xvfb defaults to 8-bit colour, which
# GUI toolkits may refuse or render incorrectly.
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
export DISPLAY=:99

wine "${MOPRO_GUI_PATH}" &

# The first run writes the roaming profile within a few seconds; the timeout
# guards against a wedged build (e.g. a broken wine prefix).
for _ in $(seq 1 60); do
    if [[ -f "${MOPRO_ROAMING_PROFILE_DIR}/mopro.ini" ]]; then
        break
    fi
    sleep 1
done

pkill MoProGUI || true
kill "${XVFB_PID}" || true

if ! [[ -f "${MOPRO_ROAMING_PROFILE_DIR}/mopro.ini" ]]; then
    echo "Error: MoProGUI did not create '${MOPRO_ROAMING_PROFILE_DIR}/mopro.ini' within 60 seconds."
    echo "The MoPro first-run initialization failed; check that wine works in this image."
    exit 3
fi

echo "MoPro first-run initialization complete: ${MOPRO_ROAMING_PROFILE_DIR}/mopro.ini"
