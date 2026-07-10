ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]
ARG QCRBOX_ROOT_DIR
ARG QCRBOX_USER


COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} MoProSuite_win_2024_10.zip /opt/wine_installations/wine_win64/drive_c/MoPro.zip

RUN cd /opt/wine_installations/wine_win64/drive_c/ && \
    unzip MoPro.zip && \
    rm MoPro.zip && \
    mv MoProSuite_win_2024_10 MoProSuite && \
    cp MoProSuite/LibMoPro/ELMAM3_beta4e.txt MoProSuite/LibMoPro/ELMAM2.txt

# These two need to be in linux filesystem path
ENV MOPRO_ROAMING_PROFILE_DIR="/opt/wine_installations/wine_win64/drive_c/users/qcrbox/AppData/Roaming/mopro"
ENV MOPRO_GUI_PATH="/opt/wine_installations/wine_win64/drive_c/MoProSuite/MoProGUI2/MoProGUI_2024_09.exe"

# These are for the mopro.ini therefore in the wine windows filesystem convention
ENV MOPRO_LIB_PATH='C:\MoProSuite\LibMoPro'
ENV MOPRO_PATH='C:\MoProSuite\bin-win\MoPro-2024-10.exe'
ENV VMOPRO_PATH='C:\MoProSuite\bin-win\VMoPro_2024_10.exe'
ENV IMOPRO_PATH='C:\MoProSuite\bin-win\Import2MoPro_2024_10.exe'
ENV MOPRO_VIEWER_PATH='C:\MoProSuite\MoProViewer\MoProViewer_2024_11.exe'

ARG QUBOX_WINE_INSTALLATIONS_DIR
ENV WINEPREFIX="/opt/wine_installations/wine_win64"
ARG WINEARCH="win64"
ENV WINEARCH=${WINEARCH}
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}

COPY configure_mopro.py ./
COPY config_mopro.yaml ./
COPY templates ./templates
COPY initialize_mopro_first_run.sh ./

# First-run initialization (roaming profile) at build time, under Xvfb: spawned
# containers must be usable immediately, so nothing may run "once" at container
# start. Runs as root (Xvfb needs /tmp/.X11-unix) with the app under gosu, like
# the crysalis-pro build-time setup.
USER root
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && \
    gosu ${QCRBOX_USER} bash -x ./initialize_mopro_first_run.sh

USER ${QCRBOX_USER}

COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./.idesktop ${QCRBOX_HOME}/.idesktop
