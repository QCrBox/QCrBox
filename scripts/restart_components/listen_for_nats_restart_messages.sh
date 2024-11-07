#!/usr/bin/env bash

set -euo pipefail

export QCRBOX_REPO=${QCRBOX_REPO:-"$(git rev-parse --show-toplevel)"}
export SCRIPT_DIR="${QCRBOX_REPO}/scripts/restart_components"
export NATS_MSG_DUMP_DIR="${SCRIPT_DIR}/restart_messages/"
export NATS_SUBJECT="restart-qcrbox-containers"


listen_to_nats_messages() {
    echo "Listening to messages on NATS subject: '${NATS_SUBJECT}'"
    echo "Messages will be dumped in the directory: ${NATS_MSG_DUMP_DIR}"
    nats sub --dump=${NATS_MSG_DUMP_DIR} ${NATS_SUBJECT} &
}


restart_components_upon_new_message() {
    while true; do
      echo "================================================"
      echo "[DDD] Beginning of while loop"
      ls -d ${NATS_MSG_DUMP_DIR}/* | entr -p -d ./restart_components.sh
      sleep 1
    done
}


main() {
    listen_to_nats_messages
    restart_components_upon_new_message
}
main
