ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]
ARG QCRBOX_ROOT_DIR
ARG QCRBOX_USER


COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} MoProSuite_win_2022_07.zip /opt/wine_installations/wine_win64/drive_c/
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} Import2MoPro-2024-07.zip /opt/wine_installations/wine_win64/drive_c/

RUN cd /opt/wine_installations/wine_win64/drive_c/ && \
    unzip MoProSuite_win_2022_07.zip && \
    rm MoProSuite_win_2022_07.zip && \
    unzip Import2MoPro-2024-07.zip -d /opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/bin-win && \
    rm Import2MoPro-2024-07.zip

ENV MOPRO_ROAMING_PROFILE_DIR="/opt/wine_installations/wine_win64/drive_c/users/qcrbox/AppData/Roaming/mopro"
ENV MOPRO_GUI_PATH="/opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/MoProGUI_Qt_win64/MoProGUI_win64.exe"
ENV MOPRO_LIB_PATH='C:\MoProSuite-win-July2022\LibMoPro'
ENV MOPRO_PATH='C:\MoProSuite-win-July2022\bin-win\MoPro-2022-06.exe'
ENV VMOPRO_PATH='C:\MoProSuite-win-July2022\bin-win\VMoPro-2022-06.exe'
ENV IMOPRO_PATH='C:\MoProSuite-win-July2022\bin-win\Import2MoPro-2024-07.exe'
ENV MOPRO_VIEWER_PATH='C:\MoProSuite-win-July2022\MoProViewer\MoProViewer_win64.exe'

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
