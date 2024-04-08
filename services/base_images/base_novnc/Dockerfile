ARG QCRBOX_DOCKER_TAG
FROM golang:1.21.4-bullseye AS easy-novnc-build
WORKDIR /src
RUN go install github.com/geek1011/easy-novnc@v1.1.0

#---------------------------------------------------------------------

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get install -y --fix-missing --no-install-recommends \
        openbox menu tigervnc-standalone-server lxterminal xdg-utils \
        xvfb xdotool x11-utils zenity idesk nautilus gedit && \
    rm -rf /var/lib/apt/lists && \
    mkdir -p /usr/share/desktop-directories

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY --from=easy-novnc-build /go/bin/easy-novnc /usr/local/bin/
COPY menu.xml /etc/xdg/openbox/

USER ${QCRBOX_USER}

COPY supervisord.base_novnc.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/
ENV DISPLAY=":0"
EXPOSE 8080
