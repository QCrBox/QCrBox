ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY configure_dummy_application.py ./

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Dummy Application"
