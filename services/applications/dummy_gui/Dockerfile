ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

COPY --chown=qcrbox:qcrbox configure_dummy_gui.py config_dummy_gui.yaml ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui_commands.py ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui.py ${QCRBOX_HOME}
