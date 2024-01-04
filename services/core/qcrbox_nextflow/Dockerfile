ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-ancestor:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

USER root
ARG QCRBOX_NEXTFLOW_HOME
ARG QCRBOX_GROUP=${QCRBOX_USER}
RUN install -d -m 0755 -o ${QCRBOX_USER} -g ${QCRBOX_GROUP} ${QCRBOX_NEXTFLOW_HOME}

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
       $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
       tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update

ARG QCRBOX_DOCKER_GID=999
RUN groupadd --gid ${QCRBOX_DOCKER_GID} docker
RUN usermod -aG docker ${QCRBOX_USER}

RUN apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

USER ${QCRBOX_USER}
RUN curl -s "https://get.sdkman.io" | bash
#    echo 'source "$HOME/.sdkman/bin/sdkman-init.sh"' >> ~/.bashrc
RUN source "$HOME/.sdkman/bin/sdkman-init.sh" && \
    sdk install java 17.0.6-amzn

ARG NEXTFLOW_VERSION
ARG NEXTFLOW_ASSET_URL=https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow-${NEXTFLOW_VERSION}-all
RUN source "$HOME/.sdkman/bin/sdkman-init.sh" && \
    wget -qO- ${NEXTFLOW_ASSET_URL} | bash && \
    chmod +x nextflow

USER root
RUN ln -s $(pwd)/nextflow /usr/local/bin/nextflow
USER ${QCRBOX_USER}

ENV NXF_HOME=${QCRBOX_NEXTFLOW_HOME}
