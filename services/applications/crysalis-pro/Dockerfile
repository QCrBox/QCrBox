ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}

USER root

SHELL ["/bin/bash", "-c"]
ARG QCRBOX_ROOT_DIR
ARG QCRBOX_USER


COPY --chown=${QCRBOX_USER}:${QCRBOX_USER} run_crysalis_pro_setup_if_not_yet_installed.sh CrysAlisPro171.44.48a.exe ${QCRBOX_ROOT_DIR}/

ARG QUBOX_WINE_INSTALLATIONS_DIR
#ARG WINEPREFIX=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64
#ENV WINEPREFIX=${WINEPREFIX}
ENV WINEPREFIX="/opt/wine_installations/wine_win64"
ARG WINEARCH="win64"
ENV WINEARCH=${WINEARCH}
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}

COPY --chown=${QCRBOX_USER}:${QCRBOX_USER} ./.idesktop ./.idesktop

RUN gosu ${QCRBOX_USER} bash -x ${QCRBOX_ROOT_DIR}/run_crysalis_pro_setup_if_not_yet_installed.sh

COPY configure_crysalis-pro.py ./
COPY config_crysalis-pro.yaml ./

ENV PATH="$PATH:/opt/crysalis-pro/bin/"

USER ${QCRBOX_USER}
