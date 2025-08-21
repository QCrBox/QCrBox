ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY ./configure_qcrboxtools.py ./
COPY ./config_qcrboxtools.yaml ./
