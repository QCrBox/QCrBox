#!/usr/bin/env bash

set -euo pipefail

export QCRBOX_REPO=${QCRBOX_REPO:-"$(git rev-parse --show-toplevel)"}
export QCRBOX_COMPONENTS=${QCRBOX_COMPONENTS:-"olex2 crystal-explorer mopro"}


abort_if_not_running_within_devbox_shell() {
    local devbox_shell_enabled=${DEVBOX_SHELL_ENABLED:-}

    if [ "${devbox_shell_enabled}" = "" ]; then
        echo "This script must be run from within a devbox shell."
        echo "Please run 'devbox shell' and then execute it again."
        exit 1
    fi
}


stop_single_docker_container() {
    local component="$1"

    echo "Stopping and removing docker container for ${component}"
    docker rm --force qcrbox-${component}-1
    echo "Stopped docker container for ${component}"
}

stop_docker_containers() {
    local components="$1"

    for component in ${components}; do
        stop_single_docker_container ${component}
    done
}


restart_docker_containers() {
    local components="$1"

    echo "Restarting docker containers for components: ${components}"
    qcb up --no-build-deps ${components}
}


restart_components() {
    local components="$1"

    echo "Restarting components: ${components}"
    echo

    stop_docker_containers "${components}"
    echo
    restart_docker_containers "${components}"
}


main() {
    abort_if_not_running_within_devbox_shell
    restart_components "${QCRBOX_COMPONENTS}"
}
main
