ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Dummy CLI"

COPY --chown=qcrbox:qcrbox \
     config_dummy_cli.yaml \
     configure_dummy_cli.py \
     ${QCRBOX_HOME}

COPY --chown=qcrbox:qcrbox --chmod=755 sample_cmd.sh ${QCRBOX_HOME}/bin/

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
