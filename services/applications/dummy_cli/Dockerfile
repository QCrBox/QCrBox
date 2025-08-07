ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

COPY --chown=qcrbox:qcrbox \
     config_dummy_cli.yaml \
     configure_dummy_cli.py \
     ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 sample_functions.py ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 sample_cmd.sh ${QCRBOX_HOME}/bin/

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
