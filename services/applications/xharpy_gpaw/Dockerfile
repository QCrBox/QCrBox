ARG QCRBOX_DOCKER_TAG
ARG QCRBOX_USER=qcrbox
ARG QCRBOX_GROUP=${QCRBOX_USER}

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]
COPY ./conda_xharpy_gpaw.yml .
RUN micromamba install -n qcrbox --file conda_xharpy_gpaw.yml --yes
COPY ./XHARPy/xharpy ./xharpy
COPY ./configure_xharpy-gpaw.py ./
COPY ./dummy.lst ./
COPY ./config_xharpy-gpaw.yaml ./