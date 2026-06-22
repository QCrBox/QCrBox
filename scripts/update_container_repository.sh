#!/usr/bin/env bash
#
# Tag a new QCrBox release and push all Docker images to GHCR.
#
# Usage:
#   bash scripts/update_container_repository.sh <version> [--tag-latest]
#
# Examples:
#   bash scripts/update_container_repository.sh 0.2.0
#   bash scripts/update_container_repository.sh 0.2.0 --tag-latest
#
# --tag-latest  After pushing versioned images, also retag and push each
#               image as :latest so the default deploy target stays current.
#
# Prerequisites:
#   docker login ghcr.io -u <github-username> -p <PAT with write:packages>
#   All private installers in place if you want to push private app images.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

VERSION=${1:?Usage: $0 <version> [--tag-latest]  e.g.  $0 0.2.0}
TAG_LATEST=0
shift
for arg in "$@"; do
    case "$arg" in
        --tag-latest) TAG_LATEST=1 ;;
        *) echo "ERROR: unknown argument '$arg'" >&2; exit 1 ;;
    esac
done

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

echo "==> Building and pushing images as $VERSION"
export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
export QCRBOX_DOCKER_TAG="$VERSION"
bash "$SCRIPT_DIR/build/push-images.sh" --all

if [ "$TAG_LATEST" -eq 1 ]; then
    echo "==> Retagging all $VERSION images as latest"
    docker images --format '{{.Repository}}:{{.Tag}}' \
        | grep "^ghcr\.io/qcrbox/.*:${VERSION}$" \
        | while IFS=: read -r repo ver; do
            docker tag "$repo:$ver" "$repo:latest"
            docker push "$repo:latest"
        done
fi

echo ""
echo "==> Done. Next steps:"
echo "    1. bash ../QCrBoxFrontend/scripts/push-frontend.sh $VERSION"
echo "       (push frontend image before deploying)"
echo "    2. git push origin $TAG"
