ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Jana2020"

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox .idesktop/* /opt/qcrbox/.idesktop/
COPY --chown=qcrbox:qcrbox \
     config_jana.yaml \
     configure_jana.py \
     ${QCRBOX_HOME}

ENV WINEPREFIX="/opt/wine_installations/wine_win64"
ARG WINEARCH="win64"
ENV WINEARCH=${WINEARCH}
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}

# Manual installion remove comment here but comment lines 30 -- 38
# COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} Jana2020Inst.msi /opt/wine_installations/wine_win64/drive_c/

# Unzipping a folder
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} Jana2020.zip /opt/wine_installations/wine_win64/drive_c/

RUN cd /opt/wine_installations/wine_win64/drive_c/ && \
    mkdir Jana2020 && \
    cd Jana2020 && \
    unzip ../Jana2020.zip && \
    rm ../Jana2020.zip

ENV JANA2020DIR='C:\Jana2020'

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

