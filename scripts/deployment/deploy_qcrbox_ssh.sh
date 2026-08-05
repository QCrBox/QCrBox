#!/usr/bin/env bash
#
# Deploy the full QCrBox stack (backend + frontend, freshly rerolled secrets)
# to a remote Ubuntu VM over SSH — e.g. an EOSC / EGI Cloud Compute
# (OpenStack) instance, or any cloud VM with a public IP.
#
# By default source repositories are cloned on the VM and images are pulled
# from GHCR. For an unpublished test deployment, --transfer-sources copies the
# local checkouts and --transfer-images streams the locally available, exactly
# tagged deployment images to the VM instead.
# For the default published-image path, publish a release first:
#   scripts/update_container_repository.sh <version>    (QCrBox images)
#   QCrBoxFrontend/scripts/push-frontend.sh <version>   (frontend image)
#
# Runs on the developer machine. Requirements:
#   - SSH access to the VM as a sudo-capable user (cloud images: 'ubuntu')
#   - docker locally when --transfer-images is used
#   - QCrBoxFrontend checked out next to QCrBox when either transfer mode is used
#   - VM internet access to install docker (and, without transfer modes, to
#     reach GitHub and GHCR)
#   - VM firewall / OpenStack security group allowing 22, 80 and 443
#
# Usage:
#   bash scripts/deployment/deploy_qcrbox_ssh.sh --host ubuntu@185.x.y.z \
#       --version 0.2.0 \
#       --ghcr-user niolon --ghcr-token ghp_xxxx \
#       [--identity ~/.ssh/eosc_key] [--domain qcrbox.example.org] \
#       [--apps "olex2_linux dummy_gui"] \
#       [--transfer-images | --reuse-remote-images] \
#       [--local-image-tag latest] [--transfer-sources] \
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem] \
#       [--update] [--no-on-demand]
#
# --update upgrades an existing installation in place (accounts, data and
# secrets survive); without it, provisioning WIPES accounts and data and
# rerolls all secrets. --no-on-demand disables the registry's on-demand
# container orchestrator (classic long-running app containers only).
#
# For development, override the cloned branch explicitly:
#   --branch <name>           clone this branch for both repos
#   --frontend-branch <name>  clone a different branch for QCrBoxFrontend only
#   --transfer-sources        copy the local QCrBox and QCrBoxFrontend trees
#   --transfer-images         copy every locally tagged image needed to deploy
#   --local-image-tag <tag>   source tag for local images (defaults to --version)
#   --reuse-remote-images     skip transfer and use exact images already on VM
#
# Omit --version to deploy :latest images from the main branch.
# Without --domain, qcrbox.<host-ip>.nip.io is used. For anything beyond a
# quick trial use a real domain: Let's Encrypt rate-limits nip.io heavily.

set -euo pipefail

HOST=""
IDENTITY=""
DOMAIN=""
APPS=""
VERSION="latest"
BRANCH=""
FRONTEND_BRANCH=""
ACME_EMAIL=""
TLS_CERT=""
TLS_KEY=""
GHCR_USER="${GHCR_USER:-}"
GHCR_TOKEN="${GHCR_TOKEN:-}"
TRANSFER_IMAGES=false
TRANSFER_SOURCES=false
REUSE_REMOTE_IMAGES=false
LOCAL_IMAGE_TAG=""
PROVISION_MODE_ARGS=()

resolve_application_dir() {
    local requested=$1 candidate spec slug
    for candidate in \
        "$QCRBOX_DIR/services/applications/$requested" \
        "$QCRBOX_DIR/services/applications/${requested//-/_}" \
        "$QCRBOX_DIR/services/applications/${requested//_/-}"; do
        if [ -d "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    # Some established CLI component names are application slugs rather than
    # directory names (notably `olex2` -> `olex2_linux`).
    for spec in "$QCRBOX_DIR"/services/applications/*/config_*.yaml; do
        [ -f "$spec" ] || continue
        slug=$(sed -nE "s/^slug:[[:space:]]*['\"]?([^'\"[:space:]]+)['\"]?[[:space:]]*$/\1/p" "$spec" | head -1)
        if [ "$slug" = "$requested" ]; then
            dirname "$spec"
            return 0
        fi
    done
    return 1
}

image_runtime_fingerprint() {
    # Docker image IDs include build history and timestamps, so clean rebuilds
    # can have different IDs while producing identical runnable images. Hash
    # only the platform, runtime configuration, and ordered filesystem layers.
    docker image inspect --format \
        '{{.Os}}/{{.Architecture}}|{{json .Config}}|{{json .RootFS.Layers}}' "$1" \
        | sha256sum | cut -d' ' -f1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --host)             HOST="$2"; shift 2 ;;
        --identity)         IDENTITY="$2"; shift 2 ;;
        --domain)           DOMAIN="$2"; shift 2 ;;
        --apps)             APPS="$2"; shift 2 ;;
        --version)          VERSION="$2"; shift 2 ;;
        --branch)           BRANCH="$2"; shift 2 ;;
        --frontend-branch)  FRONTEND_BRANCH="$2"; shift 2 ;;
        --acme-email)       ACME_EMAIL="$2"; shift 2 ;;
        --tls-cert)         TLS_CERT="$2"; shift 2 ;;
        --tls-key)          TLS_KEY="$2"; shift 2 ;;
        --ghcr-user)        GHCR_USER="$2"; shift 2 ;;
        --ghcr-token)       GHCR_TOKEN="$2"; shift 2 ;;
        --transfer-images)  TRANSFER_IMAGES=true; shift ;;
        --transfer-sources) TRANSFER_SOURCES=true; shift ;;
        --reuse-remote-images) REUSE_REMOTE_IMAGES=true; shift ;;
        --local-image-tag)  LOCAL_IMAGE_TAG="$2"; shift 2 ;;
        --update)           PROVISION_MODE_ARGS+=(--update); shift ;;
        --no-on-demand)     PROVISION_MODE_ARGS+=(--no-on-demand); shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -n "$HOST" ] || { echo "ERROR: --host user@address is required" >&2; exit 1; }
LOCAL_IMAGE_TAG="${LOCAL_IMAGE_TAG:-$VERSION}"
if [ "$TRANSFER_IMAGES" = true ] && [ "$REUSE_REMOTE_IMAGES" = true ]; then
    echo "ERROR: --transfer-images and --reuse-remote-images are mutually exclusive" >&2
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QCRBOX_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
PARENT_DIR=$(dirname "$QCRBOX_DIR")
FRONTEND_DIR="$PARENT_DIR/QCrBoxFrontend"

if [ "$TRANSFER_IMAGES" = true ] || [ "$TRANSFER_SOURCES" = true ]; then
    [ -d "$FRONTEND_DIR" ] || {
        echo "ERROR: $FRONTEND_DIR not found (the frontend must be checked out next to QCrBox)" >&2
        exit 1
    }
fi
if [ "$TRANSFER_IMAGES" = true ]; then
    command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found locally" >&2; exit 1; }
    command -v rsync >/dev/null 2>&1 || { echo "ERROR: rsync not found locally" >&2; exit 1; }
fi

# Determine git refs.
# --branch overrides --version for both repos; --frontend-branch overrides only
# the frontend. Without --branch, releases use the annotated tag and 'latest'
# tracks the main branch.
if [ -n "$BRANCH" ]; then
    QCRBOX_REF="$BRANCH"
    FRONTEND_REF="${FRONTEND_BRANCH:-$BRANCH}"
elif [ "$VERSION" = "latest" ]; then
    QCRBOX_REF="main"
    FRONTEND_REF="${FRONTEND_BRANCH:-main}"
else
    QCRBOX_REF="v$VERSION"
    FRONTEND_REF="${FRONTEND_BRANCH:-v$VERSION}"
fi

KNOWN_HOSTS=$(mktemp)
trap 'rm -f "$KNOWN_HOSTS"' EXIT
echo "==> Fetching host key for ${HOST#*@}"
ssh-keyscan -H "${HOST#*@}" >> "$KNOWN_HOSTS" 2>/dev/null \
    || { echo "ERROR: cannot reach ${HOST#*@}" >&2; exit 1; }

SSH_OPTS=(-o StrictHostKeyChecking=yes -o UserKnownHostsFile="$KNOWN_HOSTS"
          -o ServerAliveInterval=30 -o ServerAliveCountMax=6)
[ -n "$IDENTITY" ] && SSH_OPTS+=(-i "$IDENTITY")
SSH=(ssh "${SSH_OPTS[@]}" "$HOST")

echo "==> Checking SSH connectivity and sudo"
"${SSH[@]}" 'sudo -n true && echo "ssh + sudo: OK"' || {
    echo "ERROR: cannot ssh to $HOST with passwordless sudo" >&2; exit 1; }

if [ -z "$DOMAIN" ]; then
    HOST_IP=${HOST#*@}
    DOMAIN="qcrbox.$HOST_IP.nip.io"
fi
echo "==> Deploying to $HOST as https://$DOMAIN"
echo "    QCrBox:        $QCRBOX_REF"
echo "    QCrBoxFrontend: $FRONTEND_REF"
echo "    Image version:  $VERSION"
echo "    Sources:        $([ "$TRANSFER_SOURCES" = true ] && echo 'local transfer' || echo 'GitHub clone')"
if [ "$TRANSFER_IMAGES" = true ]; then
    IMAGE_MODE="local transfer"
elif [ "$REUSE_REMOTE_IMAGES" = true ]; then
    IMAGE_MODE="reuse remote"
else
    IMAGE_MODE="registry pull"
fi
echo "    Images:         $IMAGE_MODE"
[ "$TRANSFER_IMAGES" = true ] && echo "    Local image tag: $LOCAL_IMAGE_TAG"

# ----------------------------------------------------------------- docker ---
echo "==> Installing docker on the VM (if missing)"
"${SSH[@]}" 'command -v docker >/dev/null 2>&1' || "${SSH[@]}" 'sudo bash -s' <<'INSTALL_DOCKER'
apt-get update -qq
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
INSTALL_DOCKER

# ----------------------------------------------------------------- images ---
if [ "$TRANSFER_IMAGES" = true ]; then
    echo "==> Resolving the exact local image set"
    DEPLOY_REPO=$(sed -n 's/^QCRBOX_DOCKER_REPO=//p' "$QCRBOX_DIR/.env.prod" | head -1)
    [ -n "$DEPLOY_REPO" ] || { echo "ERROR: QCRBOX_DOCKER_REPO is missing from .env.prod" >&2; exit 1; }

    LOCAL_COMPOSE=(-f "$QCRBOX_DIR/docker-compose.prebuilt.yml")
    for app in $APPS; do
        app_dir=$(resolve_application_dir "$app") \
            || { echo "ERROR: application '$app' was not found" >&2; exit 1; }
        app_compose=$(find "$app_dir" -maxdepth 1 -type f -name 'docker-compose.*.prebuilt.yml' -print -quit 2>/dev/null)
        [ -n "$app_compose" ] || { echo "ERROR: no prebuilt compose file for app '$app'" >&2; exit 1; }
        LOCAL_COMPOSE+=(-f "$app_compose")
    done

    mapfile -t BACKEND_IMAGES < <(
        QCRBOX_DOCKER_REPO="$DEPLOY_REPO" QCRBOX_DOCKER_TAG="$VERSION" \
            docker compose --env-file "$QCRBOX_DIR/.env.prod" \
            "${LOCAL_COMPOSE[@]}" config --images
    )
    mapfile -t FRONTEND_IMAGES < <(
        docker compose -f "$FRONTEND_DIR/docker-compose.yml" \
            --project-directory "$FRONTEND_DIR" --project-name qcrboxfrontend \
            config --images | sed '/^qcrboxfrontend-server$/d'
    )
    ALL_IMAGES=("${BACKEND_IMAGES[@]}" "${FRONTEND_IMAGES[@]}"
                "$DEPLOY_REPO/qcrboxfrontend-server:$VERSION")
    mapfile -t ALL_IMAGES < <(printf '%s\n' "${ALL_IMAGES[@]}" | sed '/^$/d' | sort -u)

    for image_ref in "${ALL_IMAGES[@]}"; do
        local_source=""
        if [[ "$image_ref" == "$DEPLOY_REPO/"* ]]; then
            image_name=${image_ref#"$DEPLOY_REPO/"}
            image_name=${image_name%:*}
            if [ "$image_name" = qcrboxfrontend-server ]; then
                source_candidates=(
                    "qcrboxfrontend-server:$LOCAL_IMAGE_TAG"
                    "qcrbox/$image_name:$LOCAL_IMAGE_TAG"
                    "$DEPLOY_REPO/$image_name:$LOCAL_IMAGE_TAG"
                )
            else
                # qcb builds development images under qcrbox/. Prefer those
                # over possibly stale registry aliases left by an older test.
                source_candidates=(
                    "qcrbox/$image_name:$LOCAL_IMAGE_TAG"
                    "$DEPLOY_REPO/$image_name:$LOCAL_IMAGE_TAG"
                )
            fi
            for source_ref in "${source_candidates[@]}"; do
                if docker image inspect "$source_ref" >/dev/null 2>&1; then
                    local_source="$source_ref"
                    break
                fi
            done
        fi

        if [ -n "$local_source" ]; then
            if [ "$local_source" != "$image_ref" ]; then
                echo "==> Tagging local image $local_source as $image_ref"
                docker tag "$local_source" "$image_ref"
            fi
        elif docker image inspect "$image_ref" >/dev/null 2>&1; then
            # Third-party base images and an exact, already-prepared deployment
            # image have no qcb development tag to prefer.
            continue
        else
            echo "ERROR: required image '$image_ref' is not present locally" >&2
            echo "       Build or pull it first. If it has another local tag, pass" >&2
            echo "       --local-image-tag <tag> (for example, --local-image-tag latest)." >&2
            exit 1
        fi
    done

    echo "==> Comparing local and remote runtime image fingerprints"
    declare -A REMOTE_IMAGE_FINGERPRINTS=()
    while IFS=$'\t' read -r remote_ref remote_fingerprint; do
        [ -n "$remote_ref" ] && REMOTE_IMAGE_FINGERPRINTS["$remote_ref"]="$remote_fingerprint"
    done < <(
        printf '%s\n' "${ALL_IMAGES[@]}" | "${SSH[@]}" '
while IFS= read -r image_ref; do
    if image_metadata=$(sudo docker image inspect \
        --format "{{.Os}}/{{.Architecture}}|{{json .Config}}|{{json .RootFS.Layers}}" \
        "$image_ref" 2>/dev/null); then
        image_fingerprint=$(printf "%s\n" "$image_metadata" | sha256sum | cut -d" " -f1)
        printf "%s\t%s\n" "$image_ref" "$image_fingerprint"
    else
        printf "%s\t-\n" "$image_ref"
    fi
done'
    )

    CHANGED_IMAGES=()
    for image_ref in "${ALL_IMAGES[@]}"; do
        local_fingerprint=$(image_runtime_fingerprint "$image_ref")
        remote_fingerprint=${REMOTE_IMAGE_FINGERPRINTS[$image_ref]:--}
        if [ "$remote_fingerprint" = "-" ]; then
            CHANGED_IMAGES+=("$image_ref")
            echo "    missing: $image_ref"
        elif [ "$remote_fingerprint" != "$local_fingerprint" ]; then
            CHANGED_IMAGES+=("$image_ref")
            echo "    changed: $image_ref"
        fi
    done

    if [ "${#CHANGED_IMAGES[@]}" -eq 0 ]; then
        echo "==> All ${#ALL_IMAGES[@]} runtime images already match; skipping image transfer"
    else
        echo "==> ${#CHANGED_IMAGES[@]} of ${#ALL_IMAGES[@]} images need transfer"
        # Include references as well as IDs in the cache key: docker-save
        # archives contain tag metadata, so equal image content under different
        # deployment tags is not the same archive.
        ids_hash=$(
            for image_ref in "${CHANGED_IMAGES[@]}"; do
                printf '%s=%s\n' "$image_ref" "$(docker image inspect --format '{{.Id}}' "$image_ref")"
            done | sha256sum | cut -c1-12
        )
        TARBALL="/tmp/qcrbox-image-delta-$ids_hash.tar.gz"
        if [ ! -f "$TARBALL" ]; then
            echo "==> Packing ${#CHANGED_IMAGES[@]} changed images into $TARBALL"
            (umask 077; docker save "${CHANGED_IMAGES[@]}" | gzip --rsyncable --fast > "$TARBALL.partial")
            mv "$TARBALL.partial" "$TARBALL"
        else
            echo "==> Reusing image archive $TARBALL"
        fi

        printf -v RSYNC_RSH '%q ' ssh "${SSH_OPTS[@]}"
        echo "==> Transferring $(du -h "$TARBALL" | cut -f1) of changed images to the VM (resumable)"
        "${SSH[@]}" 'umask 077; mkdir -p "$HOME/.cache/qcrbox"; chmod 700 "$HOME/.cache/qcrbox"'
        rsync --partial --inplace --chmod=F600 --info=progress2 -e "$RSYNC_RSH" \
            "$TARBALL" "$HOST:.cache/qcrbox/images-delta.tar.gz"
        echo "==> Loading changed images on the VM"
        "${SSH[@]}" 'gunzip -c "$HOME/.cache/qcrbox/images-delta.tar.gz" | sudo docker load'

        echo "==> Verifying transferred runtime image fingerprints"
        TRANSFERRED_IMAGE_MANIFEST=""
        for image_ref in "${CHANGED_IMAGES[@]}"; do
            local_fingerprint=$(image_runtime_fingerprint "$image_ref")
            TRANSFERRED_IMAGE_MANIFEST+="$image_ref"$'\t'"$local_fingerprint"$'\n'
        done
        printf '%s' "$TRANSFERRED_IMAGE_MANIFEST" | "${SSH[@]}" '
while IFS="	" read -r image_ref expected_fingerprint; do
    [ -n "$image_ref" ] || continue
    image_metadata=$(sudo docker image inspect \
        --format "{{.Os}}/{{.Architecture}}|{{json .Config}}|{{json .RootFS.Layers}}" \
        "$image_ref" 2>/dev/null) || {
        echo "ERROR: transferred image is still missing: $image_ref" >&2
        exit 1
    }
    actual_fingerprint=$(printf "%s\n" "$image_metadata" | sha256sum | cut -d" " -f1)
    if [ "$actual_fingerprint" != "$expected_fingerprint" ]; then
        echo "ERROR: transferred runtime image mismatch for $image_ref" >&2
        echo "       expected $expected_fingerprint, found $actual_fingerprint" >&2
        exit 1
    fi
done'
        rm -f "$TARBALL"
    fi
fi

# ---------------------------------------------------------------- sources ---
if [ "$TRANSFER_SOURCES" = true ]; then
    echo "==> Transferring local source trees"
    tar -czf - -C "$PARENT_DIR" \
        --exclude='.git' --exclude='.devbox' --exclude='.venv' --exclude='.pixi' \
        --exclude='.build' --exclude='.ruff_cache' --exclude='.pytest_cache' \
        --exclude='__pycache__' --exclude='.local_data' --exclude='node_modules' \
        --exclude='QCrBox/services/applications/*/*.zip' \
        --exclude='QCrBox/services/applications/*/*.exe' \
        --exclude='QCrBox/.env.vm' \
        --exclude='QCrBoxFrontend/.env' \
        --exclude='QCrBoxFrontend/environment.env' \
        --exclude='QCrBoxFrontend/qcrbox_frontend/db.sqlite3' \
        --exclude='QCrBox/services/core/qcrbox_syslog/logs' \
        "$(basename "$QCRBOX_DIR")" "$(basename "$FRONTEND_DIR")" \
        | "${SSH[@]}" 'sudo bash -c '\''
set -euo pipefail
rm -rf /tmp/qcrbox-env-backup
mkdir -p /tmp/qcrbox-env-backup
cp /opt/qcrbox-src/QCrBox/.env.vm /tmp/qcrbox-env-backup/env.vm 2>/dev/null || true
cp /opt/qcrbox-src/QCrBoxFrontend/.env /tmp/qcrbox-env-backup/frontend.env 2>/dev/null || true
cp /opt/qcrbox-src/QCrBoxFrontend/environment.env /tmp/qcrbox-env-backup/frontend.environment.env 2>/dev/null || true
rm -rf /opt/qcrbox-src
mkdir -p /opt/qcrbox-src
tar -xzf - -C /opt/qcrbox-src
cp /tmp/qcrbox-env-backup/env.vm /opt/qcrbox-src/QCrBox/.env.vm 2>/dev/null || true
cp /tmp/qcrbox-env-backup/frontend.env /opt/qcrbox-src/QCrBoxFrontend/.env 2>/dev/null || true
cp /tmp/qcrbox-env-backup/frontend.environment.env /opt/qcrbox-src/QCrBoxFrontend/environment.env 2>/dev/null || true
rm -rf /tmp/qcrbox-env-backup
'\'''
else
    echo "==> Cloning source repositories on the VM"
    "${SSH[@]}" sudo bash << CLONE
set -euo pipefail
# Preserve the generated environment files across the re-clone; an --update
# run relies on them (secrets are not rerolled).
rm -rf /tmp/qcrbox-env-backup
mkdir -p /tmp/qcrbox-env-backup
cp /opt/qcrbox-src/QCrBox/.env.vm /tmp/qcrbox-env-backup/env.vm 2>/dev/null || true
cp /opt/qcrbox-src/QCrBoxFrontend/.env /tmp/qcrbox-env-backup/frontend.env 2>/dev/null || true
cp /opt/qcrbox-src/QCrBoxFrontend/environment.env /tmp/qcrbox-env-backup/frontend.environment.env 2>/dev/null || true
rm -rf /opt/qcrbox-src
mkdir -p /opt/qcrbox-src
git clone --depth 1 --branch "$QCRBOX_REF" \
    https://github.com/QCrBox/QCrBox.git /opt/qcrbox-src/QCrBox
git clone --depth 1 --branch "$FRONTEND_REF" \
    https://github.com/QCrBox/QCrBoxFrontend.git /opt/qcrbox-src/QCrBoxFrontend
cp /tmp/qcrbox-env-backup/env.vm /opt/qcrbox-src/QCrBox/.env.vm 2>/dev/null || true
cp /tmp/qcrbox-env-backup/frontend.env /opt/qcrbox-src/QCrBoxFrontend/.env 2>/dev/null || true
cp /tmp/qcrbox-env-backup/frontend.environment.env /opt/qcrbox-src/QCrBoxFrontend/environment.env 2>/dev/null || true
rm -rf /tmp/qcrbox-env-backup
CLONE
fi

# -------------------------------------------------------------------- TLS ---
PROVISION_TLS_ARGS=()
if [ -n "$TLS_CERT" ] && [ -n "$TLS_KEY" ]; then
    "${SSH[@]}" 'sudo mkdir -p /root/tls'
    "${SSH[@]}" 'sudo bash -c "cat > /root/tls/qcrbox.crt"' < "$TLS_CERT"
    "${SSH[@]}" 'sudo bash -c "cat > /root/tls/qcrbox.key"' < "$TLS_KEY"
    PROVISION_TLS_ARGS=(--tls-cert /root/tls/qcrbox.crt --tls-key /root/tls/qcrbox.key)
elif [ -n "$ACME_EMAIL" ]; then
    PROVISION_TLS_ARGS=(--acme-email "$ACME_EMAIL")
fi

# ------------------------------------------------------------- provision ----
# Deliver GHCR credentials via a root-only temp file rather than command-line
# args so the token never appears in the remote process list (ps aux).
if [ -n "$GHCR_TOKEN" ]; then
    printf 'GHCR_USER=%s\nGHCR_TOKEN=%s\n' "$GHCR_USER" "$GHCR_TOKEN" \
        | "${SSH[@]}" 'sudo bash -c "umask 077 && cat > /run/qcrbox-ghcr.env"'
fi

echo "==> Running provisioner on the VM"
PROVISION_IMAGE_ARGS=()
if [ "$TRANSFER_IMAGES" = true ] || [ "$REUSE_REMOTE_IMAGES" = true ]; then
    PROVISION_IMAGE_ARGS+=(--no-pull)
fi
PROVISION_CMD=(
    sudo bash /opt/qcrbox-src/QCrBox/scripts/deployment/provision_qcrbox.sh
    --domain "$DOMAIN"
    --source /opt/qcrbox-src
    --apps "$APPS"
    --version "$VERSION"
    "${PROVISION_TLS_ARGS[@]}"
    "${PROVISION_IMAGE_ARGS[@]}"
    "${PROVISION_MODE_ARGS[@]}"
)
# ssh joins separate command arguments with spaces before the remote shell sees
# them, losing local array boundaries. Quote every argument into one remote
# command string so a multi-application --apps value remains one argument.
printf -v PROVISION_CMD_SHELL '%q ' "${PROVISION_CMD[@]}"
"${SSH[@]}" "$PROVISION_CMD_SHELL"

echo ""
echo "=================================================================="
echo "Deployment done.  Open:  https://$DOMAIN"
echo "Credentials (also at /root/qcrbox-credentials.txt on the VM):"
"${SSH[@]}" "sudo grep -A2 'Web login' /root/qcrbox-credentials.txt"
echo "=================================================================="
