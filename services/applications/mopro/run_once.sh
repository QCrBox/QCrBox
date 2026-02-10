#!/usr/bin/env bash

# Fonts are already extracted and available in Wine prefix from Dockerfile build
# Enable RGB subpixel font smoothing to fix missing vertical strokes
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothing /t REG_SZ /d 2 /f 2>/dev/null || true
wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingType /t REG_DWORD /d 2 /f 2>/dev/null || true

# Create MoPro configuration files if they don't exist
mkdir -p "$MOPRO_ROAMING_PROFILE_DIR"

if [ ! -f "$MOPRO_ROAMING_PROFILE_DIR/mopro.ini" ]; then
    # Create mopro.ini with default paths
    sed -e "s|{{mopro_workdir}}|Z:\\home\\qcrbox|g" \
        -e "s|{{mopro_path}}|$MOPRO_PATH|g" \
        -e "s|{{vmopro_path}}|$VMOPRO_PATH|g" \
        -e "s|{{imopro_path}}|$IMOPRO_PATH|g" \
        -e "s|{{mopro_viewer_path}}|$MOPRO_VIEWER_PATH|g" \
        -e "s|{{tabl_path}}|$MOPRO_LIB_PATH\\mopro_v24.tab|g" \
        -e "s|{{wave_path}}|$MOPRO_LIB_PATH\\WAVEF_Su_Coppens_relativistic|g" \
        -e "s|{{anom_path}}|$MOPRO_LIB_PATH\\asf_Kissel.dat|g" \
        -e "s|{{dens_path}}|$MOPRO_LIB_PATH\\dens_sph_neu.tab|g" \
        /opt/qcrbox/templates/mopro.ini > "$MOPRO_ROAMING_PROFILE_DIR/mopro.ini"
fi

if [ ! -f "$MOPRO_ROAMING_PROFILE_DIR/moprogui.ini" ]; then
    sed -e "s|{{mopro_workdir}}|Z:\\home\\qcrbox|g" \
        -e "s|{{mopro_path}}|$MOPRO_PATH|g" \
        -e "s|{{vmopro_path}}|$VMOPRO_PATH|g" \
        -e "s|{{imopro_path}}|$IMOPRO_PATH|g" \
        -e "s|{{mopro_viewer_path}}|$MOPRO_VIEWER_PATH|g" \
        -e "s|{{tabl_path}}|$MOPRO_LIB_PATH\\mopro_v24.tab|g" \
        -e "s|{{wave_path}}|$MOPRO_LIB_PATH\\WAVEF_Su_Coppens_relativistic|g" \
        -e "s|{{anom_path}}|$MOPRO_LIB_PATH\\asf_Kissel.dat|g" \
        -e "s|{{dens_path}}|$MOPRO_LIB_PATH\\dens_sph_neu.tab|g" \
        /opt/qcrbox/templates/moprogui.ini > "$MOPRO_ROAMING_PROFILE_DIR/moprogui.ini"
fi

if [ ! -f "$MOPRO_ROAMING_PROFILE_DIR/moproviewer.ini" ]; then
    sed -e "s|{{mopro_workdir}}|Z:\\home\\qcrbox|g" \
        -e "s|{{mopro_path}}|$MOPRO_PATH|g" \
        -e "s|{{vmopro_path}}|$VMOPRO_PATH|g" \
        -e "s|{{imopro_path}}|$IMOPRO_PATH|g" \
        -e "s|{{mopro_viewer_path}}|$MOPRO_VIEWER_PATH|g" \
        -e "s|{{tabl_path}}|$MOPRO_LIB_PATH\\mopro_v24.tab|g" \
        -e "s|{{wave_path}}|$MOPRO_LIB_PATH\\WAVEF_Su_Coppens_relativistic|g" \
        -e "s|{{anom_path}}|$MOPRO_LIB_PATH\\asf_Kissel.dat|g" \
        -e "s|{{dens_path}}|$MOPRO_LIB_PATH\\dens_sph_neu.tab|g" \
        /opt/qcrbox/templates/moproviewer.ini > "$MOPRO_ROAMING_PROFILE_DIR/moproviewer.ini"
fi

wine $MOPRO_GUI_PATH &

sleep 2

pkill MoProGUI