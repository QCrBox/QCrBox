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

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox .idesktop/* /opt/qcrbox/.idesktop/
COPY --chown=qcrbox:qcrbox config_{{ cookiecutter.application_slug }}.yaml \
     configure_{{ cookiecutter.application_slug }}.py \
     ./
COPY --chown=qcrbox:qcrbox dummy_gui.py sample_cmd.sh /opt/{{ cookiecutter.application_slug }}/bin/

USER ${QCRBOX_USER}
WORKDIR /opt/{{ cookiecutter.application_slug }}

ENV PATH="$PATH:/opt/{{ cookiecutter.application_slug }}/bin/"
