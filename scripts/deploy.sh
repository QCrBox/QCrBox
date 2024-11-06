#! /usr/bin/env bash

set -euo pipefail

export QCRBOX_REPO=${QCRBOX_REPO:-"$(git rev-parse --show-toplevel)"}
export QCRBOX_BRANCH=${QCRBOX_BRANCH:-"dev"}
export QCRBOX_COMPONENTS=${QCRBOX_COMPONENTS:-"olex2 crystal-explorer"}


prompt_for_confirmation() {
    local answer
    read -p "Proceed? ([Y]es/[n]o): " answer
    case ${answer} in
        y|Y|"" )
            echo "Proceeding with deployment"
            ;;
        n|N|*)
            echo "Exiting deployment."
            exit 0
            ;;
    esac
}


abort_if_not_running_within_devbox_shell() {
    local devbox_shell_enabled=${DEVBOX_SHELL_ENABLED:-}

    if [ "${devbox_shell_enabled}" = "" ]; then
        echo "This script must be run from within a devbox shell."
        echo "Please run 'devbox shell' and then execute it again."
        exit 1
    fi
}

print_planned_actions() {
    local qcrbox_repo=$1
    local branch=$2
    local components=$3

    echo "- Path to QCrBox repo (set QCRBOX_REPO to override):  ${qcrbox_repo}"
    echo "- Branch to be deployed (set QCRBOX_BRANCH to override):  ${branch}"
    echo "- Components to be started (set QCRBOX_COMPONENTS to override):  ${components}"

    echo
}


remove_docker_volumes() {
    echo "Removing Docker volumes for NATS storage and QCrBox server db"
    docker volume rm -f qcrbox_qcrbox-nats-storage qcrbox_qcrbox-registry-db
}


main() {
    abort_if_not_running_within_devbox_shell
    print_planned_actions "${QCRBOX_REPO}" "${QCRBOX_BRANCH}" "${QCRBOX_COMPONENTS}"
    prompt_for_confirmation

    cd $QCRBOX_REPO
    qcb down
    remove_docker_volumes
    git checkout $QCRBOX_BRANCH
    git pull
    qcb build $QCRBOX_COMPONENTS
    qcb up --no-build $QCRBOX_COMPONENTS

    echo "Successfully deployed branch: ${QCRBOX_BRANCH}"
}
main
