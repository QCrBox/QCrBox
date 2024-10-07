ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Qcrbox Quality"

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox .idesktop/* /opt/qcrbox/.idesktop/
COPY --chown=qcrbox:qcrbox \
     config_qcrbox_quality.yaml \
     configure_qcrbox_quality.py \
     ${QCRBOX_HOME}

COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui.py sample_cmd.sh ${QCRBOX_HOME}/bin/

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
