ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get install -y --fix-missing --no-install-recommends libgtk2.0-0 libglu1-mesa openmpi-bin && \
    rm -rf /var/lib/apt/lists

# Ensure the locale en_GB is available (otherwise Olex2
# starts with an error popup and blocks the main window).
RUN sed -i 's/^# en_GB/en_GB/' /etc/locale.gen && \
    locale-gen --purge en_GB

# Dirty hack to get Olex headless to run
RUN cd /lib/x86_64-linux-gnu/ && \
    ln -s libreadline.so.8 libreadline.so.6

# create folder and then work as user to avoid a RUN chown

RUN mkdir /opt/olex2 && \
    chown -R ${QCRBOX_USER}:${QCRBOX_GROUP} /opt/olex2

COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./olex2_files/olex2-linux64_hl.zip /opt/olex2

USER ${QCRBOX_USER}

RUN cd /opt &&  \
    unzip -o olex2/olex2-linux64_hl.zip && \
    rm olex2/olex2-linux64_hl.zip && \
    # chmod +x olex2/olex2c-linux64 && \
    chmod +x olex2/startc && \
    ln -s /opt/olex2/lib/libssl.so.1.1 /opt/olex2/lib/libssl.so.10 && \
    ln -s /opt/olex2/lib/libcrypto.so.1.1 /opt/olex2/lib/libcrypto.so.10

RUN sed -i 's|^#! /bin/sh|#! /bin/bash|' /opt/olex2/start && \
    sed -i 's|^./olex2 "$@" &$|./olex2 "$@"|' /opt/olex2/start

RUN mkdir -p ${QCRBOX_HOME}/.local/share && \
    mkdir -p ${QCRBOX_HOME}/.olex2/data/ && \
    # suppress usage statistics question
    echo "QCRBOX" >> ${QCRBOX_HOME}/.olex2/data/app.token && \
    echo "ask_update=false" >> ${QCRBOX_HOME}/.olex2/data/usesettings.dat && \
    echo "confirm_on_close=false" >> ${QCRBOX_HOME}/.olex2/data/.options

ENV OLEX2_DATADIR=${QCRBOX_HOME}/.olex2/data
ENV OLEX2_DATADIR_STATIC=true

COPY ./.idesktop ${QCRBOX_HOME}/.idesktop

COPY ./configure_olex2.py ${QCRBOX_HOME}/
COPY ./olex2_glue_cli.py ${QCRBOX_HOME}
COPY ./config_olex2.yaml ${QCRBOX_HOME}


ENV QCRBOX_USER=${QCRBOX_USER}
ENV QCRBOX_HOME=${QCRBOX_HOME}
ENV PATH="$PATH:${QCRBOX_HOME}/bin/"

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY supervisord.olex2_headless.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Olex2"
ENV QCRBOX__LOGGING__LOG_LEVEL="DEBUG"
