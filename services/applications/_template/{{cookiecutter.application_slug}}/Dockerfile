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

ARG QCRBOX_APPLICATION_HOME="/opt/{{ cookiecutter.application_slug }}/"
ENV QCRBOX_APPLICATION_HOME=${QCRBOX_APPLICATION_HOME}

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox .idesktop/* /opt/qcrbox/.idesktop/
COPY --chown=qcrbox:qcrbox \
     config_{{ cookiecutter.application_slug }}.yaml \
     configure_{{ cookiecutter.application_slug }}.py \
     ${QCRBOX_APPLICATION_HOME}

COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui.py sample_cmd.sh ${QCRBOX_APPLICATION_HOME}/bin/

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_APPLICATION_HOME}

ENV PATH="$PATH:${QCRBOX_APPLICATION_HOME}/bin/"
