ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-novnc:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY MoProSuite_linux_2022_06.zip /opt/mopro/bin/
#RUN cd /opt/mopro/bin/ && \
#    unzip MoProSuite_linux_2022_06.zip && \
#    rm MoProSuite_linux_2022_06.zip &&

COPY configure_mopro.py ./
COPY config_mopro.yaml ./

ENV PATH="$PATH:/opt/mopro/bin/"
qc