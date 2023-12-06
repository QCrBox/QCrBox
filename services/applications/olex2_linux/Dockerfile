ARG QCRBOX_DOCKER_TAG

FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends libgtk2.0-0 libglu1-mesa openmpi-bin && \
    rm -rf /var/lib/apt/lists

# Ensure the locale en_GB is available (otherwise Olex2
# starts with an error popup and blocks the main window).
RUN sed -i 's/^# en_GB/en_GB/' /etc/locale.gen && \
    locale-gen --purge en_GB

# Dirty hack to get Olex headless to run
RUN cd /lib/x86_64-linux-gnu/ && \
    ln -s libreadline.so.8 libreadline.so.6

#ADD http://www2.olex2.org/olex2-distro/1.5/olex2-linux64.zip /opt/
COPY ./olex2-linux64_hl.zip /opt/
RUN cd /opt &&  \
    unzip olex2-linux64_hl.zip && \
    rm olex2-linux64_hl.zip

RUN sed -i 's|^#! /bin/sh|#! /bin/bash|' /opt/olex2/start && \
    sed -i 's|^./olex2 "$@" &$|./olex2 "$@"|' /opt/olex2/start

# RUN sed -i 's|^#! /bin/sh|#! /bin/bash|' /opt/olex2/startc

RUN chown -R ${QCRBOX_USER} /opt/olex2

USER ${QCRBOX_USER}

RUN mkdir -p ${QCRBOX_HOME}/.local/share && \
    mkdir -p ${QCRBOX_HOME}/.olex2/data/ && \
    echo "QCRBOX" >> ${QCRBOX_HOME}/.olex2/data/app.token

COPY ./.idesktop ${QCRBOX_HOME}/.idesktop

COPY ./configure_olex2.py ${QCRBOX_HOME}/
COPY ./olex2_glue_cli.py ${QCRBOX_HOME}

ENV QCRBOX_USER=${QCRBOX_USER}
ENV QCRBOX_HOME=${QCRBOX_HOME}

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY supervisord.olex2_headless.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Olex2"
WORKDIR /opt/olex2
