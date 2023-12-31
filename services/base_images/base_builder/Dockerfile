FROM debian:bookworm-20231218
SHELL ["/bin/bash", "-c"]

ARG QCRBOX_ROOT_DIR
ARG TMP_BUILD_DIR=/tmp
USER root

##
## Create user 'qcrbox'
##
ARG QCRBOX_USER=qcrbox
ARG QCRBOX_USER_UID=1000
ARG QCRBOX_HOME=${QCRBOX_ROOT_DIR}

COPY create_user_qcrbox.sh ${TMP_BUILD_DIR}
RUN bash ${TMP_BUILD_DIR}/create_user_qcrbox.sh \
        ${QCRBOX_USER} \
        ${QCRBOX_USER_UID} \
        ${QCRBOX_HOME}

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}
