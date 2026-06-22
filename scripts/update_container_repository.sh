#!/usr/bin/env bash
#
# Tag a new QCrBox release and push all Docker images to GHCR.
#
# Usage:
#   bash scripts/update_container_repository.sh <version>
#
# Example:
#   bash scripts/update_container_repository.sh 0.2.0
#
# Prerequisites:
#   docker login ghcr.io -u <github-username> -p <PAT with write:packages>
#   All private installers in place if you want to push private app images.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

VERSION=${1:?Usage: $0 <version>  e.g.  $0 0.2.0}

# Validate version looks like semver
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: version must be X.Y.Z (e.g. 0.2.0), got: $VERSION" >&2
    exit 1
fi

TAG="v$VERSION"

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "ERROR: tag $TAG already exists" >&2
    exit 1
fi

echo "==> Creating git tag $TAG"
git tag -a "$TAG" -m "Release $TAG"

echo "==> Building and pushing images as $TAG"
export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
export QCRBOX_DOCKER_TAG="$VERSION"
bash "$SCRIPT_DIR/build/push-images.sh" --all

echo ""
echo "==> Done. Push the tag with:"
echo "    git push origin $TAG"
