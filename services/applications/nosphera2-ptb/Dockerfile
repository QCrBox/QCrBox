ARG QCRBOX_DOCKER_TAG


FROM debian:trixie AS build-nosphera2

USER root

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        git ca-certificates build-essential cmake ninja-build curl && \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

RUN git clone --recursive https://github.com/AK-Kleemiss/NoSpherA2.git /tmp/NoSpherA2

WORKDIR /tmp/NoSpherA2

RUN cmake -P scripts/BootstrapMicromamba.cmake && \
    cmake --preset "release-linux" \
        -DNOSPHERA2_BUILD_TESTS=OFF -DNOSPHERA2_DEPENDENCIES_ONLY=OFF && \
    cmake --build --preset "release-linux" --parallel $(nproc)

# binary produced at: /tmp/NoSpherA2/build/release-linux/bin/NoSpherA2

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

ENV QCRBOX_APPLICATION_DISPLAY_NAME="NoSpherA2-PTB"

USER root

COPY --chown=qcrbox:qcrbox \
     config_nosphera2-ptb.yaml \
     configure_nosphera2-ptb.py \
    nosphera2_ptb_glue.py \
     ${QCRBOX_HOME}

# Install minimal runtime dependencies
RUN mkdir -p ${QCRBOX_HOME}/bin

# Copy the built NoSpherA2 binary with proper ownership and permissions
COPY --from=build-nosphera2 --chown=qcrbox:qcrbox --chmod=755 \
     /tmp/NoSpherA2/build/release-linux/bin/NoSpherA2 ${QCRBOX_HOME}/bin/NoSpherA2

# NoSpherA2 dynamically links against Intel OpenMP and TBB, which aren't part of the
# base image; install them system-wide so the loader can find them at their SONAME.
COPY --from=build-nosphera2 --chmod=755 \
     /tmp/NoSpherA2/build/release-linux/bin/libiomp5.so \
     /tmp/NoSpherA2/build/release-linux/bin/libtbb.so.12.16 \
     /usr/local/lib/
RUN ln -sf /usr/local/lib/libtbb.so.12.16 /usr/local/lib/libtbb.so.12 && ldconfig

# Download and install PTB
RUN wget https://github.com/AK-Kleemiss/ptb/releases/download/v3.8-NoSpherA2/ptb_all.zip -O /tmp/ptb_all.zip && \
    unzip /tmp/ptb_all.zip -d /tmp/ptb && \
    mv /tmp/ptb/ptb_all/ptb /tmp/ptb/ptb_all/.atompara /tmp/ptb/ptb_all/.basis_vDZP ${QCRBOX_HOME}/bin/ && \
    chmod +x ${QCRBOX_HOME}/bin/ptb && \
    chown -R qcrbox:qcrbox ${QCRBOX_HOME}/bin/ && \
    rm -rf /tmp/ptb /tmp/ptb_all.zip

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ENV PATH="$PATH:${QCRBOX_HOME}/bin/"