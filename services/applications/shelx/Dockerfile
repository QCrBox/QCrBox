ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY shelx_executables/* /opt/shelx/bin/
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} configure_shelx.py ./

ENV PATH="$PATH:/opt/shelx/bin/"
ENV QCRBOX_APPLICATION_DISPLAY_NAME="SHELX"
