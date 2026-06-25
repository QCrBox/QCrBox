#!/usr/bin/env bash
#
# Deploy the full QCrBox stack (backend + frontend, freshly rerolled secrets)
# to a remote Ubuntu VM over SSH — e.g. an EOSC / EGI Cloud Compute
# (OpenStack) instance, or any cloud VM with a public IP.
#
# Source repositories are cloned directly on the VM from GitHub.
# All images (backend + frontend) are pulled from GHCR at the specified version.
# Publish a release first:
#   scripts/update_container_repository.sh <version>    (QCrBox images)
#   QCrBoxFrontend/scripts/push-frontend.sh <version>   (frontend image)
#
# Runs on the developer machine. Requirements:
#   - SSH access to the VM as a sudo-capable user (cloud images: 'ubuntu')
#   - VM internet access (to reach GitHub and GHCR)
#   - VM firewall / OpenStack security group allowing 22, 80 and 443
#
# Usage:
#   bash scripts/deployment/deploy_qcrbox_ssh.sh --host ubuntu@185.x.y.z \
#       --version 0.2.0 \
#       --ghcr-user niolon --ghcr-token ghp_xxxx \
#       [--identity ~/.ssh/eosc_key] [--domain qcrbox.example.org] \
#       [--apps "olex2_linux dummy_gui"] \
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
#
# For development, override the cloned branch explicitly:
#   --branch <name>           clone this branch for both repos
#   --frontend-branch <name>  clone a different branch for QCrBoxFrontend only
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
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -n "$HOST" ] || { echo "ERROR: --host user@address is required" >&2; exit 1; }

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

# ---------------------------------------------------------------- sources ---
echo "==> Cloning source repositories on the VM"
"${SSH[@]}" sudo bash << CLONE
set -euo pipefail
rm -rf /opt/qcrbox-src
mkdir -p /opt/qcrbox-src
git clone --depth 1 --branch "$QCRBOX_REF" \
    https://github.com/QCrBox/QCrBox.git /opt/qcrbox-src/QCrBox
git clone --depth 1 --branch "$FRONTEND_REF" \
    https://github.com/QCrBox/QCrBoxFrontend.git /opt/qcrbox-src/QCrBoxFrontend
CLONE

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
"${SSH[@]}" sudo bash /opt/qcrbox-src/QCrBox/scripts/deployment/provision_qcrbox.sh \
    --domain "$DOMAIN" --source /opt/qcrbox-src --apps "\"$APPS\"" \
    --version "$VERSION" \
    ${PROVISION_TLS_ARGS[@]+"${PROVISION_TLS_ARGS[@]}"}

echo ""
echo "=================================================================="
echo "Deployment done.  Open:  https://$DOMAIN"
echo "Credentials (also at /root/qcrbox-credentials.txt on the VM):"
"${SSH[@]}" "sudo grep -A2 'Web login' /root/qcrbox-credentials.txt"
echo "=================================================================="
