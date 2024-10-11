ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Qcrbox Quality"

RUN conda install -n qcrbox -c conda-forge plotly bokeh

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox \
     config_qcrbox_quality.yaml \
     configure_qcrbox_quality.py \
     qcrbox_quality_module.py \
     ${QCRBOX_HOME}

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
