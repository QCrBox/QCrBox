ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y gfortran g++ git liblapack-dev cmake coreutils gawk tofrodos libblas-dev libblas3 && \
    git clone --recurse-submodules https://github.com/dylan-jayatilaka/tonto.git && \
    cd tonto && \
    git checkout release-no-ptr && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_Fortran_COMPILER=gfortran -DCOMPILE_LAPACK=ON && \
    make -j && \
    chown -R ${QCRBOX_USER}:${QCRBOX_GROUP} /opt/qcrbox/tonto/

COPY configure_tonto_lamagoet.py ./
COPY config_tonto_lamagoet.yaml ./

USER qcrbox

ENV PATH="$PATH:/opt/qcrbox/tonto/build"
