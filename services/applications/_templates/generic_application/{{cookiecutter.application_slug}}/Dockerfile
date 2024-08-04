ARG QCRBOX_DOCKER_TAG
{% if cookiecutter.application_type == "CLI" %}
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
{% elif cookiecutter.application_type == "GUI (Linux)" %}
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}
{% elif cookiecutter.application_type == "GUI (Windows)" %}
FROM qcrbox/base-wine:${QCRBOX_DOCKER_TAG}
{% else %}
FROM qcrbox/INVALID-INVALID-INVALID
{% endif %}

SHELL ["/bin/bash", "-c"]

COPY sample_cmd.sh /opt/{{ cookiecutter.application_slug }}/bin/
COPY configure_{{ cookiecutter.application_slug }}.py ./
COPY config_{{ cookiecutter.application_slug }}.yaml ./

ENV PATH="$PATH:/opt/{{ cookiecutter.application_slug }}/bin/"
