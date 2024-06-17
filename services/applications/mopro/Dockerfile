ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]
ARG QCRBOX_ROOT_DIR
ARG QCRBOX_USER


COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} MoProSuite_win_2022_07.zip /opt/wine_installations/wine_win64/drive_c/

RUN cd /opt/wine_installations/wine_win64/drive_c/ && \
    unzip MoProSuite_win_2022_07.zip && \
    rm MoProSuite_win_2022_07.zip

ARG QUBOX_WINE_INSTALLATIONS_DIR
ENV WINEPREFIX="/opt/wine_installations/wine_win64"
ARG WINEARCH="win64"
ENV WINEARCH=${WINEARCH}
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}

COPY configure_mopro.py ./
COPY config_mopro.yaml ./
COPY templates ./templates

COPY run_once.sh .
RUN bash ./run_once.sh && \
    rm run_once.sh

#ENV PATH="$PATH:/opt/mopro-win"
USER ${QCRBOX_USER}

