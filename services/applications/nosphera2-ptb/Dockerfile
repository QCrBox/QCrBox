ARG QCRBOX_DOCKER_TAG


FROM alpine:3.22 AS build-nosphera2

USER root

# Install build dependencies in Alpine (musl-based)
RUN apk add --no-cache \
        build-base \
        cmake \
        git \
        gfortran \
        pkgconfig \
        curl \
        ca-certificates \
        file \
        patchelf \
        python3 \
        ninja \
        linux-headers \
        bash \
        musl-utils \
        cargo \
        && rm -rf /var/cache/apk/*

SHELL ["/bin/bash", "-c"]

# Required RUSTFLAGS for Rust 1.80 compatibility
ENV RUSTFLAGS="-A dangerous_implicit_autorefs"

# Build NoSpherA2 with musl (naturally static)
RUN git clone --recursive https://github.com/AK-Kleemiss/NoSpherA2.git /tmp/NoSpherA2 && \
    cd /tmp/NoSpherA2 && \
    echo "=== Checking build environment ===" && \
    gcc --version && \
    echo "=== Checking submodules ===" && \
    git submodule status && \
    echo "=== Applying fixes for musl compatibility ===" && \
    find . -name "makefile*" -exec sed -i 's/-std=c++2b/-std=c++20/g' {} \; && \
    sed -i 's#\./../BasisSetConverter ../Windows/#./../BasisSetConverter ../Linux/#g' Linux/makefile_basis_set_converter && \
    echo "=== Modifying makefiles for musl static linking ===" && \
    sed -i 's/LIBS := -Wl,-Bstatic -lstdc++ -lpthread -Wl,-Bdynamic -lm -lc/LIBS := -static -lstdc++ -lpthread -lm/g' Linux/makefile && \
    sed -i 's/GCC_OPTS := -std=c++20 -O3 -c -fmessage-length=0 -fopenmp -static -MMD -MP -msse2 -msse3 -msse4.1 -msse4.2 -mavx -ffast-math/GCC_OPTS := -std=c++20 -O3 -c -fmessage-length=0 -fopenmp -static -MMD -MP -msse2 -msse3 -msse4.1 -msse4.2 -mavx -ffast-math -D_GNU_SOURCE/g' Linux/makefile && \
    sed -i 's/GCC_OPTS_DEBUG := -std=c++20 -Og -g -c -fmessage-length=0 -static -MMD -MP -msse2 -msse3 -msse4.1 -msse4.2 -mavx -ffast-math/GCC_OPTS_DEBUG := -std=c++20 -Og -g -c -fmessage-length=0 -static -MMD -MP -msse2 -msse3 -msse4.1 -msse4.2 -mavx -ffast-math -D_GNU_SOURCE/g' Linux/makefile && \
    sed -i 's/@${COMP} -o "BasisSetConverter" ${BASIS_OBJS}/@${COMP} -static -o "BasisSetConverter" ${BASIS_OBJS}/g' Linux/makefile_basis_set_converter && \
    sed -i 's/cmake .. -DCMAKE_C_COMPILER=${C_COMP} -DCMAKE_CXX_COMPILER=${COMP} -DCMAKE_BUILD_TYPE=Release -DLIBOMP_ENABLE_SHARED=OFF/cmake .. -DCMAKE_C_COMPILER=${C_COMP} -DCMAKE_CXX_COMPILER=${COMP} -DCMAKE_BUILD_TYPE=Release -DLIBOMP_ENABLE_SHARED=OFF -DLIBOMP_OMPT_SUPPORT=OFF -DLIBOMP_ARCHER_SUPPORT=OFF -DLIBOMP_STATS=OFF -DCMAKE_C_FLAGS="-D_GNU_SOURCE" -DCMAKE_CXX_FLAGS="-D_GNU_SOURCE"/g' makefile && \
    echo "=== Building with musl (static by default) ===" && \
    make omp -j$(nproc) && \
    make featomic -j$(nproc) && \
    make all -j$(nproc)

FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}

SHELL ["/bin/bash", "-c"]

ENV QCRBOX__NATS__HOST="qcrbox-nats"
ENV QCRBOX__REGISTRY__SERVER__HOST="qcrbox-registry"
ENV QCRBOX__REGISTRY__SERVER__PORT="8000"

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
     /tmp/NoSpherA2/NoSpherA2 ${QCRBOX_HOME}/bin/NoSpherA2

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