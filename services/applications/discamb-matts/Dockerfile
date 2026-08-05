ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}


SHELL ["/bin/bash", "-c"]

RUN rm -f /opt/qcrbox/.idesktop/default.lnk
COPY --chown=qcrbox:qcrbox \
     config_discamb-matts.yaml \
     configure_discamb-matts.py \
     discamb_matts_glue.py \
     ${QCRBOX_HOME}
COPY --chown=qcrbox:qcrbox --chmod=755 discambMATTS2tsc_2026_02_20_linux "${QCRBOX_HOME}/bin/discambMATTS2tsc"


USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"
