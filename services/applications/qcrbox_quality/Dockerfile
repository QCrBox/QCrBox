ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-ancestor:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Qcrbox Quality"

# pyqcrbox already installs its pinned svcs/typing-extensions pair in the
# base image. Installing svcs again through conda can upgrade only svcs and
# leave an incompatible pip-installed typing_extensions behind.
RUN micromamba install -n qcrbox -c conda-forge bokeh numpy django && \
    micromamba clean --all --yes
RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox \
     django_minimal.py \
     start_dev_webserver.sh \
     ${QCRBOX_HOME}

ADD templates ${QCRBOX_HOME}/templates
ADD quality_html ${QCRBOX_HOME}/quality_html

RUN chmod +x start_dev_webserver.sh

COPY --chown=qcrbox:qcrbox \
     supervisord.quality_webserver.conf \
        ${QCRBOX_HOME}/supervisord_conf

USER ${QCRBOX_USER}
ENV QCRBOX_HOME=${QCRBOX_HOME}

WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="DataDisplay"
ENV QCRBOX__LOGGING__LOG_LEVEL="DEBUG"

EXPOSE 8080

# Supervisord staying alive is not sufficient: deployment and Traefik need to
# know that the Django process is actually accepting requests.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --start-interval=1s \
    CMD curl --fail --silent --show-error http://127.0.0.1:8080/ >/dev/null || exit 1
