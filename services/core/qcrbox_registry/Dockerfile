ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-ancestor:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

ENV QCRBOX__REGISTRY__SERVER__HOST="0.0.0.0"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

HEALTHCHECK \
    --interval=60s \
    --start-period=60s \
    --start-interval=1s \
    CMD curl --fail http://127.0.0.1:${QCRBOX__REGISTRY__SERVER__PORT}/api/healthz || exit 1


ARG QCRBOX_REGISTRY_DB_DIR=${QCRBOX_REGISTRY_DB_DIR}
#ENV QCRBOX_REGISTRY_DB_DIR=${QCRBOX_REGISTRY_DB_DIR}
ENV QCRBOX_DB_URL="sqlite:///${QCRBOX_REGISTRY_DB_DIR}/pyqcrbox_registry_db.sqlite"
RUN mkdir -p ${QCRBOX_REGISTRY_DB_DIR}
RUN chown ${QCRBOX_USER}:${QCRBOX_GROUP} ${QCRBOX_REGISTRY_DB_DIR}
VOLUME ${QCRBOX_REGISTRY_DB_DIR}

# Registry-only Python dependencies (on-demand container orchestration).
# Deliberately not installed via base-ancestor so that application containers
# do not ship the Docker API client. The requirements file is copied into this
# build context by `qcb build` (see cli/subcommands/build.py).
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} requirements-orchestrator.txt ${QCRBOX_HOME}/
RUN ${QCRBOX_PYTHON_VENV_DIR}/bin/python -m pip install -r ${QCRBOX_HOME}/requirements-orchestrator.txt

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY supervisord.qcrbox_registry_server.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/
