ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-ancestor:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

HEALTHCHECK \
    --interval=5s \
    CMD test -f /tmp/SENTINEL_QCRBOX_CLIENT_STARTUP_SUCCESSFUL.txt || exit 1

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY supervisord.base_application.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/
RUN ln -s ${APP_HOME}/set_container_qcrbox_id.sh /etc/profile.d/qcrbox.sh && \
    #echo "source /etc/profile" >> ${APP_HOME}/.bashrc && \
    #echo 'export ENV=/etc/profile' >> "${APP_HOME}/.profile" && \
    true

ENV ENV="/etc/profile"
