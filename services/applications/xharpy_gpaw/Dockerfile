ARG QCRBOX_DOCKER_TAG
ARG QCRBOX_USER=qcrbox
ARG QCRBOX_GROUP=${QCRBOX_USER}

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]
COPY ./conda_xharpy_gpaw.yml .
RUN micromamba install -n qcrbox --file conda_xharpy_gpaw.yml --yes && \
    micromamba clean --all --yes 
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./XHARPy ./xharpy
RUN cd /opt/qcrbox/xharpy && \
    micromamba run -n qcrbox python -m pip install .
COPY ./configure_xharpy_gpaw.py ./
COPY ./dummy.lst ./
COPY ./config_xharpy_gpaw.yaml ./
