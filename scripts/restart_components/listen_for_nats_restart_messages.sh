#!/usr/bin/env bash

set -euo pipefail

export QCRBOX_REPO=${QCRBOX_REPO:-"$(git rev-parse --show-toplevel)"}


main() {
    nats subscribe "restart-qcrbox-containers" | \
        tee -a ${QCRBOX_REPO}/scripts/restart_components/nats_restart_messages.txt
}
main
