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

# Install wine (https://www.winehq.org/)
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    curl -o /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    curl -O --output-dir /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/trixie/winehq-trixie.sources && \
    apt-get update -y && \
    apt-get install -y --install-recommends "winehq-${WINE_BRANCH}=${WINE_VERSION}" "wine-${WINE_BRANCH}=${WINE_VERSION}" && \
    rm -rf /var/lib/apt/lists && \
    true

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
        ${WINEPREFIX_WIN64}

# Win32 prefix: straightforward with dual-arch wine (works because i386 is present)
RUN export WINEARCH="win32" && \
    export WINEPREFIX="${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32" && \
    gosu ${QCRBOX_USER} bash -c 'winetricks corefonts && winetricks fontsmooth=rgb'

# Win64 prefix: with i386 installed wine defaults to win32 even when WINEARCH=win64.
# Fix: temporarily remove i386 so wine enters "new WoW64 mode" and creates a real win64
# prefix. winetricks corefonts fails in that mode because it calls syswow64/regedit.exe
# which doesn't exist without i386. Work around by:
#   1. Running wineboot --init to create the win64 prefix structure
#   2. Copying fonts from the already-initialised win32 prefix (avoids re-downloading)
#   3. Using 64-bit `wine reg` (system32, not syswow64) to register them + set fontsmooth
#   4. Reinstalling i386 so the win32 prefix works at runtime
RUN dpkg --remove --force-depends "wine-stable-i386:i386" && \
    export WINEARCH="win64" && \
    export WINEPREFIX="${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64" && \
    gosu ${QCRBOX_USER} bash -c 'wineboot --init' && \
    cp "${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win32/drive_c/windows/Fonts/"*.ttf \
       "${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64/drive_c/windows/Fonts/" && \
    gosu ${QCRBOX_USER} bash -c '\
        for f in "${WINEPREFIX}/drive_c/windows/Fonts/"*.ttf; do \
            name="$(basename "${f%.ttf}")"; \
            wine reg add "HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts" \
                /v "${name} (TrueType)" /d "$(basename "$f")" /f 2>/dev/null || true; \
        done && \
        wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothing /t REG_SZ /d 2 /f && \
        wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingType /t REG_DWORD /d 2 /f && \
        wine reg add "HKCU\\Control Panel\\Desktop" /v FontSmoothingGamma /t REG_DWORD /d 0x578 /f \
    ' && \
    apt-get update -y && \
    apt-get install -y --install-recommends "wine-stable-i386=${WINE_VERSION}" && \
    rm -rf /var/lib/apt/lists

# Create device Y: pointing to the shared files directory
ARG QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH
RUN mkdir -p "${WINEPREFIX_WIN32}/dosdevices/" && \
    ln -f -s "${QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH}" "${WINEPREFIX_WIN32}/dosdevices/y:"
RUN mkdir -p "${WINEPREFIX_WIN64}/dosdevices/" && \
    ln -f -s "${QCRBOX_SHARED_FILES_DIR_CONTAINER_PATH}" "${WINEPREFIX_WIN64}/dosdevices/y:"

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
