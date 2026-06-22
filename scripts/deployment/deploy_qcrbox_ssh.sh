#!/usr/bin/env bash
#
# Deploy the full QCrBox stack (backend + frontend, freshly rerolled secrets)
# to a remote Ubuntu VM over SSH — e.g. an EOSC / EGI Cloud Compute
# (OpenStack) instance, or any cloud VM with a public IP.
#
# Runs on the developer machine. Requirements:
#   - SSH access to the VM as a sudo-capable user (cloud images: 'ubuntu')
#   - docker locally with the QCrBox images built (streamed to the VM unless
#     --no-images is given)
#   - the QCrBoxFrontend repository checked out next to QCrBox
#   - VM firewall / OpenStack security group allowing 22, 80 and 443
#
# Usage:
#   bash scripts/deployment/deploy_qcrbox_ssh.sh --host ubuntu@185.x.y.z \
#       [--identity ~/.ssh/eosc_key] [--domain qcrbox.example.org] \
#       [--apps "olex2_linux dummy_gui"] [--no-images] \
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
#
# Without --domain, qcrbox.<host-ip>.nip.io is used. For anything beyond a
# quick trial use a real domain: Let's Encrypt rate-limits nip.io heavily.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QCRBOX_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
PARENT_DIR=$(dirname "$QCRBOX_DIR")
FRONTEND_DIR="$PARENT_DIR/QCrBoxFrontend"

HOST=""
IDENTITY=""
DOMAIN=""
APPS=""
ACME_EMAIL=""
TLS_CERT=""
TLS_KEY=""
TRANSFER_IMAGES=1

while [ $# -gt 0 ]; do
    case "$1" in
        --host)       HOST="$2"; shift 2 ;;
        --identity)   IDENTITY="$2"; shift 2 ;;
        --domain)     DOMAIN="$2"; shift 2 ;;
        --apps)       APPS="$2"; shift 2 ;;
        --acme-email) ACME_EMAIL="$2"; shift 2 ;;
        --tls-cert)   TLS_CERT="$2"; shift 2 ;;
        --tls-key)    TLS_KEY="$2"; shift 2 ;;
        --no-images)  TRANSFER_IMAGES=0; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -n "$HOST" ] || { echo "ERROR: --host user@address is required" >&2; exit 1; }
[ -d "$FRONTEND_DIR" ] || { echo "ERROR: $FRONTEND_DIR not found" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found" >&2; exit 1; }

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
if [ "$TRANSFER_IMAGES" -eq 1 ]; then
    core_images=(
        "traefik:v3.6"
        "authelia/authelia:4.38"
        "lldap/lldap:v0.6.1-alpine"
        "nats:2.10.16-alpine"
        "balabit/syslog-ng:latest"
        "qcrbox/registry:latest"
    )
    app_images=()
    for app in $APPS; do
        app_compose=$(ls "$QCRBOX_DIR/services/applications/$app"/docker-compose.*.run.yml 2>/dev/null | head -1)
        [ -n "$app_compose" ] || { echo "ERROR: no run compose file for app '$app'" >&2; exit 1; }
        img=$(grep -m1 -E '^\s*image:' "$app_compose" \
            | sed -e 's/^\s*image:\s*//' -e 's/["'"'"']//g' \
            | sed -e 's/\${QCRBOX_DOCKER_TAG[^}]*}/latest/')
        app_images+=("$img")
    done

    if ! docker image inspect qcrboxfrontend-server >/dev/null 2>&1; then
        docker compose -f "$FRONTEND_DIR/docker-compose.yml" \
            --project-directory "$FRONTEND_DIR" --project-name qcrboxfrontend \
            build server
    fi
    all_images=("${core_images[@]}" "${app_images[@]}" "qcrboxfrontend-server:latest" "postgres:14.0-alpine" "nginx:1.23-alpine")
    for img in "${all_images[@]}"; do
        docker image inspect "$img" >/dev/null 2>&1 || {
            echo "ERROR: image '$img' not present locally — build it first (qcb build)" >&2
            exit 1
        }
    done

    # Pack all images into one local tarball (named after the image IDs, so a
    # stale tarball from a previous run is never reused), then rsync it: if
    # the connection drops, rerunning the script resumes the upload instead
    # of starting over.
    ids_hash=$(docker image inspect -f '{{.Id}}' "${all_images[@]}" | sha256sum | cut -c1-12)
    TARBALL="/tmp/qcrbox-images-$ids_hash.tar.gz"
    if [ ! -f "$TARBALL" ]; then
        echo "==> Packing images into $TARBALL"
        docker save "${all_images[@]}" | gzip --fast > "$TARBALL.partial"
        mv "$TARBALL.partial" "$TARBALL"
    else
        echo "==> Reusing packed images at $TARBALL"
    fi

    echo "==> Syncing $(du -h "$TARBALL" | cut -f1) to the VM (resumable — rerun on interruption)"
    rsync --partial --inplace --info=progress2 -e "ssh ${SSH_OPTS[*]}" \
        "$TARBALL" "$HOST:/tmp/qcrbox-images.tar.gz"

    echo "==> Loading images on the VM"
    "${SSH[@]}" 'gunzip -c /tmp/qcrbox-images.tar.gz | sudo docker load && rm /tmp/qcrbox-images.tar.gz'
    rm -f "$TARBALL"
fi

# ---------------------------------------------------------------- sources ---
echo "==> Transferring source trees"
tar -czf - -C "$PARENT_DIR" \
    --exclude='.git' --exclude='.devbox' --exclude='.venv' \
    --exclude='__pycache__' --exclude='.local_data' --exclude='node_modules' \
    --exclude='QCrBoxFrontend/qcrbox_frontend/db.sqlite3' \
    --exclude='QCrBox/services/core/qcrbox_syslog/logs' \
    "$(basename "$QCRBOX_DIR")" "$(basename "$FRONTEND_DIR")" \
    | "${SSH[@]}" 'sudo rm -rf /opt/qcrbox-src && sudo mkdir -p /opt/qcrbox-src && sudo tar -xzf - -C /opt/qcrbox-src'

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
echo "==> Running provisioner on the VM"
"${SSH[@]}" sudo bash /opt/qcrbox-src/QCrBox/scripts/deployment/provision_qcrbox.sh \
    --domain "$DOMAIN" --source /opt/qcrbox-src --apps "\"$APPS\"" \
    ${PROVISION_TLS_ARGS[@]+"${PROVISION_TLS_ARGS[@]}"}

echo ""
echo "=================================================================="
echo "Deployment done.  Open:  https://$DOMAIN"
echo "Credentials (also at /root/qcrbox-credentials.txt on the VM):"
"${SSH[@]}" "sudo grep -A2 'Web login' /root/qcrbox-credentials.txt"
echo "=================================================================="
