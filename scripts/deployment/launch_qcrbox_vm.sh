#!/usr/bin/env bash
#
# Create a local Multipass VM running the full QCrBox stack (backend +
# frontend) with freshly rerolled secrets — a self-contained deployment
# rehearsal that avoids /etc/hosts editing by using nip.io wildcard DNS.
#
# Runs on the developer machine. Requires:
#   - multipass (Linux/macOS) or multipass.exe (Windows install, callable
#     from WSL; install with: winget install Canonical.Multipass)
#   - docker with the QCrBox images already built (they are streamed into
#     the VM, nothing is rebuilt inside it)
#   - the QCrBoxFrontend repository checked out next to QCrBox
#
# Usage:
#   bash scripts/deployment/launch_qcrbox_vm.sh \
#       [--name qcrbox-vm] [--apps "olex2_linux dummy_gui"] \
#       [--domain qcrbox.example.org] \
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem] \
#       [--cpus 4] [--memory 8G] [--disk 60G]
#
# Without --domain, the hostname is derived from the VM IP via nip.io
# (e.g. qcrbox.192.168.64.5.nip.io), which resolves in any browser without
# hosts-file changes (requires internet DNS; some routers' rebind protection
# blocks nip.io answers).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
QCRBOX_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
PARENT_DIR=$(dirname "$QCRBOX_DIR")
FRONTEND_DIR="$PARENT_DIR/QCrBoxFrontend"

VM_NAME="qcrbox-vm"
APPS=""
DOMAIN=""
ACME_EMAIL=""
TLS_CERT=""
TLS_KEY=""
CPUS=4
MEMORY="8G"
DISK="60G"

while [ $# -gt 0 ]; do
    case "$1" in
        --name)       VM_NAME="$2"; shift 2 ;;
        --apps)       APPS="$2"; shift 2 ;;
        --domain)     DOMAIN="$2"; shift 2 ;;
        --acme-email) ACME_EMAIL="$2"; shift 2 ;;
        --tls-cert)   TLS_CERT="$2"; shift 2 ;;
        --tls-key)    TLS_KEY="$2"; shift 2 ;;
        --cpus)       CPUS="$2"; shift 2 ;;
        --memory)     MEMORY="$2"; shift 2 ;;
        --disk)       DISK="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ----------------------------------------------------------------- tooling --
# The Windows installer does not always end up on PATH inside WSL, so also
# probe the default install location.
MP_WIN_DEFAULT="/mnt/c/Program Files/Multipass/bin/multipass.exe"
if command -v multipass >/dev/null 2>&1; then
    MP=multipass
elif command -v multipass.exe >/dev/null 2>&1; then
    MP=multipass.exe
elif [ -x "$MP_WIN_DEFAULT" ]; then
    MP="$MP_WIN_DEFAULT"
else
    echo "ERROR: multipass not found." >&2
    echo "  Windows (for WSL users): winget install Canonical.Multipass" >&2
    echo "  Linux: sudo snap install multipass" >&2
    exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found" >&2; exit 1; }
[ -d "$FRONTEND_DIR" ] || { echo "ERROR: $FRONTEND_DIR not found" >&2; exit 1; }

# ----------------------------------------------------------- collect images --
core_images=(
    "traefik:v3.1.1"
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

echo "==> Frontend image"
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

# ------------------------------------------------------------------ VM ------
if ! "$MP" info "$VM_NAME" >/dev/null 2>&1; then
    echo "==> Launching VM '$VM_NAME' (Ubuntu 24.04, $CPUS cpus, $MEMORY ram, $DISK disk)"
    "$MP" launch noble --name "$VM_NAME" --cpus "$CPUS" --memory "$MEMORY" --disk "$DISK"
else
    echo "==> Reusing existing VM '$VM_NAME'"
fi

VM_IP=$("$MP" exec "$VM_NAME" -- hostname -I | awk '{print $1}' | tr -d '\r')
[ -n "$VM_IP" ] || { echo "ERROR: could not determine VM IP" >&2; exit 1; }
if [ -z "$DOMAIN" ]; then
    DOMAIN="qcrbox.$VM_IP.nip.io"
fi
echo "==> VM IP: $VM_IP   domain: $DOMAIN"

echo "==> Installing docker in the VM"
"$MP" exec "$VM_NAME" -- sudo bash -c 'command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh'

echo "==> Transferring source trees (this can take a minute)"
tar -czf - -C "$PARENT_DIR" \
    --exclude='.git' --exclude='.devbox' --exclude='.venv' \
    --exclude='__pycache__' --exclude='.local_data' --exclude='node_modules' \
    --exclude='QCrBoxFrontend/qcrbox_frontend/db.sqlite3' \
    "$(basename "$QCRBOX_DIR")" "$(basename "$FRONTEND_DIR")" \
    | "$MP" exec "$VM_NAME" -- sudo bash -c 'rm -rf /opt/qcrbox-src && mkdir -p /opt/qcrbox-src && tar -xzf - -C /opt/qcrbox-src'

echo "==> Streaming docker images into the VM (tens of GB — be patient)"
docker save "${all_images[@]}" | gzip --fast \
    | "$MP" exec "$VM_NAME" -- sudo bash -c 'gunzip | docker load'

# Supplied certificate: copy into the VM and point the provisioner at it
PROVISION_TLS_ARGS=()
if [ -n "$TLS_CERT" ] && [ -n "$TLS_KEY" ]; then
    "$MP" exec "$VM_NAME" -- sudo mkdir -p /root/tls
    "$MP" exec "$VM_NAME" -- sudo bash -c 'cat > /root/tls/qcrbox.crt' < "$TLS_CERT"
    "$MP" exec "$VM_NAME" -- sudo bash -c 'cat > /root/tls/qcrbox.key' < "$TLS_KEY"
    PROVISION_TLS_ARGS=(--tls-cert /root/tls/qcrbox.crt --tls-key /root/tls/qcrbox.key)
elif [ -n "$ACME_EMAIL" ]; then
    PROVISION_TLS_ARGS=(--acme-email "$ACME_EMAIL")
fi

echo "==> Running provisioner in the VM"
"$MP" exec "$VM_NAME" -- sudo bash /opt/qcrbox-src/QCrBox/scripts/deployment/provision_qcrbox.sh \
    --domain "$DOMAIN" --source /opt/qcrbox-src --apps "$APPS" \
    ${PROVISION_TLS_ARGS[@]+"${PROVISION_TLS_ARGS[@]}"}

echo ""
echo "=================================================================="
echo "VM '$VM_NAME' is up.  Open:  https://$DOMAIN"
echo "Credentials (also at /root/qcrbox-credentials.txt in the VM):"
"$MP" exec "$VM_NAME" -- sudo grep -A2 'Web login' /root/qcrbox-credentials.txt
echo ""
echo "Manage the VM:  $MP stop|start|delete $VM_NAME"
echo "=================================================================="
