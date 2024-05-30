ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY configure_cod_check.py ./
COPY config_cod_check.yaml ./
COPY ./simple_cod_module.py ./

RUN micromamba install -n qcrbox requests --yes

