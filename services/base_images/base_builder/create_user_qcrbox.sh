#!/usr/bin/env bash

set -euo pipefail

QCRBOX_USER=$1
QCRBOX_GROUP=${QCRBOX_USER}
QCRBOX_USER_UID=$2
QCRBOX_USER_GID=${QCRBOX_USER_UID}
QCRBOX_HOME=$3

groupadd --gid ${QCRBOX_USER_GID} ${QCRBOX_GROUP} && \
    useradd --home-dir ${QCRBOX_HOME} --shell /bin/bash --uid ${QCRBOX_USER_UID} --gid ${QCRBOX_USER_GID} ${QCRBOX_USER} && \
    install -d -m 0755 -o ${QCRBOX_USER} -g ${QCRBOX_GROUP} ${QCRBOX_HOME}

echo "Created new user:"
echo "  User name: ${QCRBOX_USER}"
echo "  Group name: ${QCRBOX_GROUP}"
echo "  UID: ${QCRBOX_USER_UID}"
echo "  GID: ${QCRBOX_USER_GID}"
echo "  Home directory: ${QCRBOX_HOME}"
