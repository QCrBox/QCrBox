ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

USER root

SHELL ["/bin/bash", "-c"]

#ARG WINE_BRANCH=staging
ARG WINE_BRANCH=stable
#ARG MONO_VERSION=9.0.0
ARG MONO_VERSION=10.3.0
#ARG GECKO_VERSION=2.47.4
ARG GECKO_VERSION=2.47.4

# Install wine (https://www.winehq.org/)
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    curl -o /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    curl -O --output-dir /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/trixie/winehq-trixie.sources && \
    apt-get update -y && \
    apt-get install -y --install-recommends winehq-${WINE_BRANCH} wine-${WINE_BRANCH} && \
    rm -rf /var/lib/apt/lists && \
    true

# Install cabextract (needed to extract font files) and fontconfig
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends cabextract fontconfig && \
    rm -rf /var/lib/apt/lists

# Manually install Microsoft Core Fonts (ARM-compatible approach)
# Download and extract the core fonts that Windows applications expect
RUN mkdir -p /usr/share/fonts/truetype/msttcorefonts && \
    cd /tmp && \
    for font in andale32.exe arial32.exe arialb32.exe comic32.exe courie32.exe georgi32.exe impact32.exe times32.exe trebuc32.exe verdan32.exe webdin32.exe; do \
        wget -q https://downloads.sourceforge.net/project/corefonts/the%20fonts/final/$font && \
        cabextract -q -d /usr/share/fonts/truetype/msttcorefonts $font && \
        rm $font; \
    done && \
    chmod 644 /usr/share/fonts/truetype/msttcorefonts/*

# Install Mono (https://wiki.winehq.org/Mono)
RUN mkdir -p /opt/wine-${WINE_BRANCH}/share/wine/mono && \
    wget -O - https://dl.winehq.org/wine/wine-mono/${MONO_VERSION}/wine-mono-${MONO_VERSION}-x86.tar.xz | tar -Jxv -C /opt/wine-${WINE_BRANCH}/share/wine/mono

# Install Gecko (https://wiki.winehq.org/Gecko)
RUN mkdir -p /opt/wine-${WINE_BRANCH}/share/wine/gecko && \
    wget -O /opt/wine-${WINE_BRANCH}/share/wine/gecko/wine-gecko-${GECKO_VERSION}-x86.msi https://dl.winehq.org/wine/wine-gecko/${GECKO_VERSION}/wine-gecko-${GECKO_VERSION}-x86.msi && \
    wget -O /opt/wine-${WINE_BRANCH}/share/wine/gecko/wine-gecko-${GECKO_VERSION}-x86_64.msi https://dl.winehq.org/wine/wine-gecko/${GECKO_VERSION}/wine-gecko-${GECKO_VERSION}-x86_64.msi

# Install winetricks (https://wiki.winehq.org/Winetricks) and bash completion for winetricks
RUN wget -O /usr/local/bin/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks && \
    chmod +x /usr/local/bin/winetricks && \
    wget -O /usr/share/bash-completion/completions/winetricks \
            https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks.bash-completion

# Note: The value of QCRBOX_WINE_INSTALLATIONS_DIR is defined in `.env.dev`.
#       It passed here by `docker-compose.yml` using a build arg.
ARG QCRBOX_WINE_INSTALLATIONS_DIR

# During the build process we create WINEPREFIX directories for
# both win32 and win64. This allows us to select the version
# used by the running container using the environment variable
# QCRBOX_WINEARCH (which is only defined during runtime).
ARG WINEPREFIX_WIN32=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32
ARG WINEPREFIX_WIN64=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64

RUN mkdir -p \
        ${QCRBOX_WINE_INSTALLATIONS_DIR}\
        ${WINEPREFIX_WIN32} \
        ${WINEPREFIX_WIN64} && \
    chown ${QCRBOX_USER}:${QCRBOX_USER} \
        ${QCRBOX_WINE_INSTALLATIONS_DIR} \
        ${WINEPREFIX_WIN32} \
        ${WINEPREFIX_WIN64} #&& \
    #chmod 777 ${APP_HOME}

# Initialize Wine prefixes without downloading fonts (using native Liberation fonts instead)
# Using wineboot --init to create Wine prefix structure without executing Windows installers
# This allows the image to build on ARM via QEMU without hanging
RUN export WINEARCH="win32" && \
    export WINEPREFIX="${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32" && \
    gosu ${QCRBOX_USER} bash -c 'DISPLAY= WINEDLLOVERRIDES="mscoree,mshtml=" wineboot --init'
RUN export WINEARCH="win64" && \
    export WINEPREFIX="${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64" && \
    gosu ${QCRBOX_USER} bash -c 'DISPLAY= WINEDLLOVERRIDES="mscoree,mshtml=" wineboot --init'

# Configure fontconfig to use RGB subpixel rendering (fixes missing vertical strokes)
RUN mkdir -p /etc/fonts/conf.d && \
    echo '<?xml version="1.0"?>\n\
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n\
<fontconfig>\n\
  <match target="font">\n\
    <edit name="rgba" mode="assign">\n\
      <const>rgb</const>\n\
    </edit>\n\
  </match>\n\
</fontconfig>' > /etc/fonts/local.conf

# Update font cache so Wine can find the system fonts
RUN fc-cache -f -v

# Copy fonts into Wine prefixes so Qt and other Windows apps can find them
# Wine applications (especially Qt-based GUIs) need fonts in C:\windows\Fonts
# Copy instead of symlink to ensure proper ownership and access
RUN mkdir -p ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32/drive_c/windows/Fonts \
             ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64/drive_c/windows/Fonts && \
    cp /usr/share/fonts/truetype/msttcorefonts/* ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32/drive_c/windows/Fonts/ && \
    cp /usr/share/fonts/truetype/msttcorefonts/* ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64/drive_c/windows/Fonts/ && \
    chown -R ${QCRBOX_USER}:${QCRBOX_USER} \
        ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32/drive_c/windows/Fonts \
        ${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64/drive_c/windows/Fonts

USER ${QCRBOX_USER}

ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ARG QCRBOX_HOME=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_HOME=${QCRBOX_HOME}
ONBUILD ENV QCRBOX_HOME=${QCRBOX_HOME}

ARG QCRBOX_WINEARCH=${QCRBOX_WINEARCH}
ENV WINEARCH=${QCRBOX_WINEARCH}
ENV WINEPREFIX=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_${QCRBOX_WINEARCH}
