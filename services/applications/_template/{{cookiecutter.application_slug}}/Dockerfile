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

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="{{ cookiecutter.application_name }}"

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox .idesktop/* /opt/qcrbox/.idesktop/
COPY --chown=qcrbox:qcrbox \
     config_{{ cookiecutter.application_slug }}.yaml \
     configure_{{ cookiecutter.application_slug }}.py \
     ${QCRBOX_HOME}

COPY --chown=qcrbox:qcrbox --chmod=755 dummy_gui.py sample_cmd.sh ${QCRBOX_HOME}/bin/

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
