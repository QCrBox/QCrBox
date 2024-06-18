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

Xvfb :99 &
export DISPLAY=:99

wine /opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/MoProGUI_Qt_win64/MoProGUI_win64.exe &

until xdotool search --name "MoPro"
do
    echo "..."
    sleep 1
done

xdotool search --name "MoPro" windowfocus
xdotool key Alt+F4
xdotool key Enter

unset DISPLAY
killall Xvfb
