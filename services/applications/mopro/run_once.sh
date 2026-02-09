#!/usr/bin/env bash

# Fonts are already extracted and available in Wine prefix from Dockerfile build
# Enable RGB subpixel font smoothing to fix missing vertical strokes
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothing /t REG_SZ /d 2 /f 2>/dev/null || true
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingType /t REG_DWORD /d 2 /f 2>/dev/null || true

wine $MOPRO_GUI_PATH &

sleep 2

pkill MoProGUI