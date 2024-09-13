ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]
ARG QCRBOX_ROOT_DIR
ARG QCRBOX_USER


COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} MoProSuite_win_2024_09.zip /opt/wine_installations/wine_win64/drive_c/

RUN cd /opt/wine_installations/wine_win64/drive_c/ && \
    unzip MoProSuite_win_2024_09.zip && \
    rm MoProSuite_win_2024_09.zip
# These two need to be in linux filesystem path
ENV MOPRO_ROAMING_PROFILE_DIR="/opt/wine_installations/wine_win64/drive_c/users/qcrbox/AppData/Roaming/mopro"
ENV MOPRO_GUI_PATH="/opt/wine_installations/wine_win64/drive_c/MoProSuite_2024_09/MoProGUI2/MoProGUI_2024_09.exe"

# These are for the mopro.ini therefore in the wine windows filesystem convention
ENV MOPRO_LIB_PATH='C:\MoProSuite_2024_09\LibMoPro'
ENV MOPRO_PATH='C:\MoProSuite_2024_09\bin-win\MoPro_2024_09.exe'
ENV VMOPRO_PATH='C:\MoProSuite_2024_09\bin-win\VMoPro_2024_09.exe'
ENV IMOPRO_PATH='C:\MoProSuite_2024_09\bin-win\Import2MoPro_2024_09.exe'
ENV MOPRO_VIEWER_PATH='C:\MoProSuite_2024_09\MoProViewer\MoProViewer_2024_v1.1_3200.exe'

ARG QUBOX_WINE_INSTALLATIONS_DIR
ENV WINEPREFIX="/opt/wine_installations/wine_win64"
ARG WINEARCH="win64"
ENV WINEARCH=${WINEARCH}
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}

COPY configure_mopro.py ./
COPY config_mopro.yaml ./
COPY templates ./templates
COPY run_once.sh ./

COPY supervisord.mopro_sh.conf ${QCRBOX_SUPERVISORD_CONF_DIR}

USER ${QCRBOX_USER}

COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./.idesktop ${QCRBOX_HOME}/.idesktop
