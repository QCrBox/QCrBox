ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

USER root

SHELL ["/bin/bash", "-c"]

#ARG WINE_BRANCH=staging
ARG WINE_BRANCH=stable
ARG WINE_VERSION=11.0.0.0~trixie-1
#ARG MONO_VERSION=9.0.0
ARG MONO_VERSION=10.3.0
#ARG GECKO_VERSION=2.47.4
ARG GECKO_VERSION=2.47.4

# Install wine 64-bit only — no i386 / win32 support.
# All current QCrBox wine apps (crysalis-pro, mopro) require win64 and explicitly
# reject win32. Skipping dpkg --add-architecture i386 avoids cross-arch package
# conflicts that can occur in Debian trixie when amd64 and i386 builds of ffmpeg
# libraries are out of sync.
# WINE_VERSION pins the exact WineHQ build; update it deliberately when upgrading.
RUN mkdir -pm755 /etc/apt/keyrings && \
    curl -o /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    curl -O --output-dir /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/trixie/winehq-trixie.sources && \
    apt-get update -y && \
    apt-get install -y --install-recommends \
        "wine-${WINE_BRANCH}-amd64=${WINE_VERSION}" && \
    rm -rf /var/lib/apt/lists && \
    true

# Install Mono (https://wiki.winehq.org/Mono)
RUN mkdir -p /opt/wine-${WINE_BRANCH}/share/wine/mono && \
    wget -O - https://dl.winehq.org/wine/wine-mono/${MONO_VERSION}/wine-mono-${MONO_VERSION}-x86.tar.xz | tar -Jxv -C /opt/wine-${WINE_BRANCH}/share/wine/mono

# Install Gecko (https://wiki.winehq.org/Gecko) — 64-bit only
RUN mkdir -p /opt/wine-${WINE_BRANCH}/share/wine/gecko && \
    wget -O /opt/wine-${WINE_BRANCH}/share/wine/gecko/wine-gecko-${GECKO_VERSION}-x86_64.msi \
        https://dl.winehq.org/wine/wine-gecko/${GECKO_VERSION}/wine-gecko-${GECKO_VERSION}-x86_64.msi

# Install winetricks (https://wiki.winehq.org/Winetricks) and bash completion for winetricks
RUN wget -O /usr/local/bin/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/local/bin/winetricks && \
    wget -O /usr/share/bash-completion/completions/winetricks \
            https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks.bash-completion

# Note: The value of QCRBOX_WINE_INSTALLATIONS_DIR is defined in `.env.dev`.
#       It passed here by `docker-compose.yml` using a build arg.
ARG QCRBOX_WINE_INSTALLATIONS_DIR

ARG WINEPREFIX_WIN64=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64

RUN mkdir -p \
        ${QCRBOX_WINE_INSTALLATIONS_DIR} \
        ${WINEPREFIX_WIN64} && \
    chown ${QCRBOX_USER}:${QCRBOX_USER} \
        ${QCRBOX_WINE_INSTALLATIONS_DIR} \
        ${WINEPREFIX_WIN64}

# Install fonts and enable font smoothing
RUN export WINEARCH="win64" && \
    export WINEPREFIX="${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64" && \
    gosu ${QCRBOX_USER} bash -c 'winetricks corefonts && winetricks fontsmooth=rgb'

# Create device Y: pointing to the shared files directory
ARG QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH
RUN mkdir -p "${WINEPREFIX_WIN64}/dosdevices/" && \
    ln -f -s "${QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH}" "${WINEPREFIX_WIN64}/dosdevices/y:"

USER ${QCRBOX_USER}

ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ARG QCRBOX_HOME=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_HOME=${QCRBOX_HOME}
ONBUILD ENV QCRBOX_HOME=${QCRBOX_HOME}

ENV WINEARCH=win64
ENV WINEPREFIX=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64
