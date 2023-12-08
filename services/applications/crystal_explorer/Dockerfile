ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

USER root

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends libglu1-mesa libqt5core5a libqt5gui5 libqt5opengl5 libqt5widgets5 && \
    rm -rf /var/lib/apt/lists

COPY ./CrystalExplorer-21.5-ubuntu-20.04.deb /tmp/
RUN cd /tmp &&  \
    dpkg -i CrystalExplorer-21.5-ubuntu-20.04.deb && \
    rm CrystalExplorer-*.deb

COPY --chown=${QCRBOX_USER}:${QCRBOX_USER} ./.idesktop ${QCRBOX_HOME}/.idesktop
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} supervisord.crystal_explorer.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} CrystalExplorer21.conf ${QCRBOX_HOME}/.config/crystalexplorer.net/
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} configure_crystal_explorer.py ${QCRBOX_HOME}/

USER ${QCRBOX_USER}

ENV QCRBOX_APPLICATION_DISPLAY_NAME="CrystalExplorer"
