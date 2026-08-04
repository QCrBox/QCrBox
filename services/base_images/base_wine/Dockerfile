ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

USER root

SHELL ["/bin/bash", "-c"]

# Wine 11.0 has a GDI text-rendering regression which makes MoProGUI's
# small UI font illegible. 11.1 includes the upstream corrupted-text fix.
# Keep this exact development build pinned until that fix reaches stable.
ARG WINE_BRANCH=devel
ARG WINE_VERSION=11.1~trixie-1
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
    apt-get install -y --install-recommends \
        "winehq-${WINE_BRANCH}=${WINE_VERSION}" \
        "wine-${WINE_BRANCH}=${WINE_VERSION}" \
        "wine-${WINE_BRANCH}-amd64=${WINE_VERSION}" \
        "wine-${WINE_BRANCH}-i386:i386=${WINE_VERSION}" && \
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

# A single dual-architecture win64 prefix: 64-bit and (via WoW64) 32-bit
# Windows applications both work — required by MoPro/CrysAlisPro, whose
# suites mix 64-bit GUIs with 32-bit computational tools. This needs the
# i386 wine package installed at runtime (the WineHQ amd64 package ships no
# 32-bit PE files).
#
# Two pitfalls, discovered the hard way:
#   1. With both architectures installed, the plain `wine` launcher picks the
#      i386 loader even when WINEARCH=win64, which can create a win32 prefix
#      (or deadlock). Prefix creation must use the 64-bit loader explicitly.
#   2. Removing i386 for prefix creation and reinstalling it afterwards (the
#      previous approach) produces a "new WoW64 mode" prefix that dual-arch
#      wine cannot use at all ("could not load kernel32.dll, c0000135") and
#      that lacks syswow64 entirely, so 32-bit tools were always broken.
#
# KNOWN LIMITATION: dual-architecture prefix creation (wineboot processing
# wine.inf) deadlocks on WSL2 kernels — observed with wine 10.0 and 11.0,
# with and without seccomp/init/privileged. Build this image on a native
# Linux host or in CI (see .github/workflows/build-base-images.yml); the
# timeout below turns the deadlock into a loud, explained failure.
ARG WINEPREFIX_WIN64=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64
ARG WINE64_LOADER=/opt/wine-${WINE_BRANCH}/lib/wine/x86_64-unix/wine

RUN mkdir -p \
        ${QCRBOX_WINE_INSTALLATIONS_DIR}\
        ${WINEPREFIX_WIN64} && \
    chown ${QCRBOX_USER}:${QCRBOX_USER} \
        ${QCRBOX_WINE_INSTALLATIONS_DIR} \
        ${WINEPREFIX_WIN64}

RUN export WINEARCH="win64" && \
    export WINEPREFIX="${WINEPREFIX_WIN64}" && \
    export WINE="${WINE64_LOADER}" && \
    { timeout 1200 gosu ${QCRBOX_USER} bash -c "${WINE64_LOADER} wineboot --init && wineserver --wait" || { \
        echo "ERROR: wine prefix creation did not finish within 20 minutes."; \
        echo "Dual-architecture wine prefix creation is known to deadlock on WSL2 kernels."; \
        echo "Build this image on a native Linux host or via the build-base-images CI workflow,"; \
        echo "and pull it from GHCR on WSL2 machines."; \
        exit 1; \
    }; } && \
    test -f "${WINEPREFIX_WIN64}/drive_c/windows/syswow64/ntdll.dll" || { \
        echo "ERROR: the win64 prefix has no syswow64 - 32-bit applications would not work."; \
        exit 1; \
    } && \
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

# Only the dual-arch win64 prefix exists (it runs 32-bit apps via WoW64).
ENV WINEARCH=win64
ENV WINEPREFIX=${QCRBOX_WINE_INSTALLATIONS_DIR}/wine_win64
