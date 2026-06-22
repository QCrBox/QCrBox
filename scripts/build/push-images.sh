#!/usr/bin/env bash
#
# Build and push QCrBox Docker images to a container registry.
#
# All images should be pushed as a matching set to avoid version mismatches
# between the registry and application containers.
#
# Prerequisites:
#   export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox
#   export QCRBOX_DOCKER_TAG=latest
#   docker login ghcr.io -u <github-username> -p <PAT with write:packages>
#
# Usage:
#   push-images.sh --all                    # full release: base → registry → apps
#   push-images.sh --base                   # base images only (dependency order)
#   push-images.sh registry                 # registry only
#   push-images.sh olex2_linux              # specific public app
#   push-images.sh crysalis-pro             # specific private app (checks installer)
#   push-images.sh --base registry olex2_linux   # combine as needed

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QCRBOX_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

REPO=${QCRBOX_DOCKER_REPO:?Set QCRBOX_DOCKER_REPO, e.g. export QCRBOX_DOCKER_REPO=ghcr.io/qcrbox}
TAG=${QCRBOX_DOCKER_TAG:?Set QCRBOX_DOCKER_TAG, e.g. export QCRBOX_DOCKER_TAG=latest}

# Base images must be built in this exact order (each depends on the previous)
BASE_IMAGES=(base-ancestor base-application base-novnc base-wine)
BASE_DIRS=(
    services/base_images/base_ancestor
    services/base_images/base_application
    services/base_images/base_novnc
    services/base_images/base_wine
)

# ---------------------------------------------------------------------------

_build_and_push() {
    local name=$1 context=$2
    shift 2
    echo "==> Building $name → $REPO/$name:$TAG"
    # Tag locally as qcrbox/<name>:$TAG so subsequent builds resolve FROM directives
    # without pulling from the remote registry.
    docker build "$@" \
        -t "$REPO/$name:$TAG" \
        -t "qcrbox/$name:$TAG" \
        "$QCRBOX_DIR/$context"
    docker push "$REPO/$name:$TAG"
}

_build_base_images() {
    for i in "${!BASE_IMAGES[@]}"; do
        local name="${BASE_IMAGES[$i]}" dir="${BASE_DIRS[$i]}"
        local args=()
        [[ "$name" != "base-ancestor" ]] && args+=(--build-arg "QCRBOX_DOCKER_TAG=$TAG")
        _build_and_push "$name" "$dir" "${args[@]}"
    done
}

_build_registry() {
    _build_and_push "registry" "services/core/qcrbox_registry" \
        --build-arg "QCRBOX_DOCKER_TAG=$TAG"
}

_build_app() {
    local app=$1
    local app_dir="$QCRBOX_DIR/services/applications/$app"
    [[ -d "$app_dir" ]] || { echo "ERROR: no application directory for '$app'" >&2; exit 1; }

    # Run any prebuild download scripts (e.g. for crystal_explorer, olex2_linux)
    for script in "$app_dir"/prebuild__*.py; do
        [[ -f "$script" ]] || continue
        echo "==> Running $(basename "$script")"
        python3 "$script"
    done

    # Check private installer deps if sentinel is present
    local sentinel="$app_dir/private_build.yml"
    if [[ -f "$sentinel" ]]; then
        python3 "$SCRIPT_DIR/_check_private_deps.py" "$sentinel" "$app_dir"
    fi

    _build_and_push "$app" "services/applications/$app" \
        --build-arg "QCRBOX_DOCKER_TAG=$TAG"
}

_discover_public_apps() {
    find "$QCRBOX_DIR/services/applications" -name "docker-compose.*.prebuilt.yml" \
        | xargs -n1 dirname | sort -u \
        | while IFS= read -r dir; do
            [[ -f "$dir/private_build.yml" ]] && continue
            basename "$dir"
        done
}

_discover_private_apps() {
    find "$QCRBOX_DIR/services/applications" -name "private_build.yml" \
        | xargs -n1 dirname | sort -u | xargs -n1 basename
}

# ---------------------------------------------------------------------------

if [[ $# -eq 0 ]]; then
    echo "Usage: $(basename "$0") --all | --base | registry | <app> [...]"
    echo ""
    echo "  --all      Full release: base images → registry → public apps → private apps"
    echo "  --base     Base images only (in dependency order)"
    echo "  registry   Registry service only"
    echo "  <app>      Application by directory name"
    echo ""
    echo "Public apps:  $(_discover_public_apps | tr '\n' ' ')"
    echo "Private apps: $(_discover_private_apps | tr '\n' ' ')"
    exit 1
fi

BUILD_BASE=0
BUILD_REGISTRY=0
BUILD_ALL=0
NAMED_APPS=()

for arg in "$@"; do
    case "$arg" in
        --all)      BUILD_ALL=1 ;;
        --base)     BUILD_BASE=1 ;;
        registry)   BUILD_REGISTRY=1 ;;
        -*)         echo "ERROR: unknown flag '$arg'" >&2; exit 1 ;;
        *)          NAMED_APPS+=("$arg") ;;
    esac
done

if [[ "$BUILD_ALL" -eq 1 ]]; then
    _build_base_images
    _build_registry
    for app in $(_discover_public_apps); do
        _build_app "$app"
    done
    # For private apps: warn and skip if installer is missing rather than aborting
    # the whole release — not every maintainer has every installer.
    for app in $(_discover_private_apps); do
        sentinel="$QCRBOX_DIR/services/applications/$app/private_build.yml"
        if python3 "$SCRIPT_DIR/_check_private_deps.py" "$sentinel" "$QCRBOX_DIR/services/applications/$app" 2>/dev/null; then
            _build_app "$app"
        else
            echo "SKIP: $app — installer not present (see $sentinel)"
        fi
    done
else
    [[ "$BUILD_BASE" -eq 1 ]]     && _build_base_images
    [[ "$BUILD_REGISTRY" -eq 1 ]] && _build_registry
    for app in "${NAMED_APPS[@]}"; do
        _build_app "$app"
    done
fi

echo "==> Done."
