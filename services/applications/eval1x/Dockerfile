ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get install -y --fix-missing --no-install-recommends libgfortran5 tk8.6 blt ncompress imagemagick libc6 && \
    apt-get remove vim -y && \
    rm -rf /var/lib/apt/lists

# somehow xfonts-base is not available via apt but replacement package is missing 9x15 font required for eval
RUN cd /opt &&  \
    wget --auth-no-challenge https://ftp.debian.org/debian/pool/main/x/xfonts-encodings/xfonts-encodings_1.0.4-2.2_all.deb && \
    dpkg -i xfonts-encodings_1.0.4-2.2_all.deb && \
    rm xfonts-encodings_1.0.4-2.2_all.deb && \
    wget --auth-no-challenge https://ftp.debian.org/debian/pool/main/x/xfonts-utils/xfonts-utils_7.7+6_amd64.deb && \
    dpkg -i xfonts-utils_7.7+6_amd64.deb && \
    rm xfonts-utils_7.7+6_amd64.deb && \
    wget --auth-no-challenge https://ftp.debian.org/debian/pool/main/x/xfonts-base/xfonts-base_1.0.5_all.deb && \
    dpkg -i xfonts-base_1.0.5_all.deb && \
    rm xfonts-base_1.0.5_all.deb

# RUN apt-get install -y xfonts-base

RUN micromamba install -c conda-forge -n base --yes python=3.10 numpy scipy matplotlib pmw && \
    micromamba clean --all -y

RUN mkdir /opt/utrecht && \
    chown -R ${QCRBOX_USER}:${QCRBOX_GROUP} /opt/utrecht

USER ${QCRBOX_USER}

# unpack eval
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./EVPY-Linux-x86_64-20231113-bullseye.tar.gz /opt/utrecht
RUN cd /opt &&  \
    tar xvfz utrecht/EVPY-Linux-x86_64-20231113-bullseye.tar.gz && \
    rm utrecht/EVPY-Linux-x86_64-20231113-bullseye.tar.gz

COPY ./.idesktop ${QCRBOX_HOME}/.idesktop
COPY ./configure_eval1x.py ${QCRBOX_HOME}/
COPY ./config_eval1x.yaml ${QCRBOX_HOME}/

ENV QCRBOX_USER=${QCRBOX_USER}
ENV QCRBOX_HOME=${QCRBOX_HOME}
ENV PATH "/opt/utrecht/bin:$PATH"

ENV QCRBOX_APPLICATION_DISPLAY_NAME="Eval14/15"
