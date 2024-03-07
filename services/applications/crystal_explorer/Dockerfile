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

USER ${QCRBOX_USER}

COPY supervisord.crystal_explorer.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/
COPY CrystalExplorer21.conf ${QCRBOX_HOME}/.config/crystalexplorer.net/
COPY --chown=${QCRBOX_USER}:${QCRBOX_USER} ./.idesktop ${QCRBOX_HOME}/.idesktop
COPY ./config_crystal_explorer.yaml ${QCRBOX_HOME}/
COPY configure_crystal_explorer.py ${QCRBOX_HOME}/

ENV QCRBOX_APPLICATION_DISPLAY_NAME="CrystalExplorer"
