ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY shelx_executables/* /opt/shelx/bin/
COPY configure_shelx.py ./

ENV PATH="$PATH:/opt/shelx/bin/"
