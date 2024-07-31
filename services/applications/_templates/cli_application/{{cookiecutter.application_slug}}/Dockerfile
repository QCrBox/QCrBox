ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root

# Add dependencies that need installing as root here

USER ${QCRBOX_USER}

# files can be added via yml to the mamba environment as such
# RUN micromamba install -n qcrbox --file conda_packages.yml --yes && \
#     micromamba clean --all --yes

COPY sample_cmd.sh /opt/{{ cookiecutter.application_slug }}/bin/
COPY configure_{{ cookiecutter.application_slug }}.py ./
COPY config_{{ cookiecutter.application_slug }}.yaml ./

ENV PATH="$PATH:/opt/{{ cookiecutter.application_slug }}/bin/"
