ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY sample_cmd.sh /opt/{{ cookiecutter.application_slug }}/bin/
COPY configure_{{ cookiecutter.application_slug }}.py ./
COPY config_{{ cookiecutter.application_slug }}.yaml ./

ENV PATH="$PATH:/opt/{{ cookiecutter.application_slug }}/bin/"
