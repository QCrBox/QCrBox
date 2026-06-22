#!/usr/bin/env bash
#
# Build and push application images that require private installers.
#
# Prerequisites:
#   docker login ghcr.io -u <github-username> -p <PAT with write:packages>
#
# Usage:
#   bash scripts/build/push-apps.sh [app ...]
#
# With no arguments, builds all apps that have a private_build.yml sentinel.
# With app names, builds only those (e.g. "crysalis-pro mopro").

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QCRBOX_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

REPO=${QCRBOX_DOCKER_REPO:?Set QCRBOX_DOCKER_REPO, e.g. export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox}
TAG=${QCRBOX_DOCKER_TAG:?Set QCRBOX_DOCKER_TAG, e.g. export QCRBOX_DOCKER_TAG=latest}

if [ $# -eq 0 ]; then
    apps=$(find "$QCRBOX_DIR/services/applications" -name private_build.yml \
           | xargs -n1 dirname | xargs -n1 basename)
else
    apps="$*"
fi

for app in $apps; do
    sentinel="$QCRBOX_DIR/services/applications/$app/private_build.yml"
    [ -f "$sentinel" ] || { echo "ERROR: no private_build.yml for '$app'" >&2; exit 1; }

    python3 "$SCRIPT_DIR/_check_private_deps.py" "$sentinel" "$QCRBOX_DIR/services/applications/$app"

    echo "==> Building $app → $REPO/$app:$TAG"
    docker buildx build \
        --build-arg QCRBOX_DOCKER_TAG="$TAG" \
        --tag "$REPO/$app:$TAG" \
        --push \
        "$QCRBOX_DIR/services/applications/$app"
done

echo "==> Done."
