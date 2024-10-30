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


print_planned_actions() {
    local qcrbox_repo=$1
    local branch=$2
    local components=$3

    echo "- Path to QCrBox repo (set QCRBOX_REPO to override):  ${qcrbox_repo}"
    echo "- Branch to be deployed (set QCRBOX_BRANCH to override):  ${branch}"
    echo "- Components to be started (set QCRBOX_COMPONENTS to override):  ${components}"

    echo
}


main() {
    print_planned_actions "${QCRBOX_REPO}" "${QCRBOX_BRANCH}" "${QCRBOX_COMPONENTS}"
    prompt_for_confirmation

    cd $QCRBOX_REPO
    devbox run qcb down
    devbox run git checkout $QCRBOX_BRANCH
    devbox run git pull
    devbox run qcb build $QCRBOX_COMPONENTS
    devbox run qcb up --no-build $QCRBOX_COMPONENTS

    echo "Deployment successful"
}
main
