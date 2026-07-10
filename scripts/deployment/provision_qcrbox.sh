#!/usr/bin/env bash
#
# Provision a fresh Ubuntu VM (or server) with the full QCrBox stack:
# backend (Traefik + Authelia + registry + applications) and the web frontend,
# with every secret freshly generated ("rerolled") for this installation.
#
# This script runs INSIDE the target machine as root (or via sudo). It expects
# the source trees at <source>/QCrBox and <source>/QCrBoxFrontend.
# All images (backend + frontend) are pulled from GHCR at the specified version.
#
# WARNING: a fresh install (the default) WIPES all accounts and frontend data
# and rerolls every secret. To upgrade an existing installation in place
# (keeping accounts, data and secrets), pass --update.
#
# TLS modes (pick one):
#   default                          self-signed certificate (local/LAN VMs)
#   --acme-email <email>             Let's Encrypt (publicly reachable hosts)
#   --tls-cert <crt> --tls-key <key> supplied certificate, e.g. from your
#                                    institution's CA. Must cover <domain>,
#                                    auth./api.registry./traefik.<domain> and
#                                    *.gui.<domain>.
#
# Usage:
#   sudo bash provision_qcrbox.sh --domain qcrbox.10.2.3.4.nip.io \
#       [--source /opt/qcrbox-src] [--apps "olex2_linux dummy_gui"] \
#       [--ghcr-user niolon --ghcr-token ghp_xxxx] \
#       [--frontend-image ghcr.io/qcrbox/qcrboxfrontend:0.2.0] \
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem] \
#       [--update] [--no-on-demand]
#
# Secrets are written to /root/qcrbox-credentials.txt (mode 600).
#
# On-demand containers: by default the registry's orchestrator is enabled with
# per-container resource limits (8 GB RAM / 4 CPUs, 10 instances total) so app
# containers are spawned per user on demand; adjust the limits in .env.vm.
# Pass --no-on-demand for the classic mode with only long-running containers.

set -euo pipefail

DOMAIN=""
SOURCE_DIR="/opt/qcrbox-src"
APPS=""
VERSION="latest"
ACME_EMAIL=""
TLS_CERT=""
TLS_KEY=""
GHCR_USER="${GHCR_USER:-}"
GHCR_TOKEN="${GHCR_TOKEN:-}"
UPDATE=false
ON_DEMAND=true

while [ $# -gt 0 ]; do
    case "$1" in
        --domain)       DOMAIN="$2"; shift 2 ;;
        --source)       SOURCE_DIR="$2"; shift 2 ;;
        --apps)         APPS="$2"; shift 2 ;;
        --version)      VERSION="$2"; shift 2 ;;
        --acme-email)   ACME_EMAIL="$2"; shift 2 ;;
        --tls-cert)     TLS_CERT="$2"; shift 2 ;;
        --tls-key)      TLS_KEY="$2"; shift 2 ;;
        --ghcr-user)    GHCR_USER="$2"; shift 2 ;;
        --ghcr-token)   GHCR_TOKEN="$2"; shift 2 ;;
        --update)       UPDATE=true; shift ;;
        --no-on-demand) ON_DEMAND=false; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -n "$DOMAIN" ] || { echo "ERROR: --domain is required" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root (sudo)" >&2; exit 1; }

# Load GHCR credentials from the temp file written by the deploy script.
# Using a file rather than command-line args keeps the token out of ps aux.
if [ -f /run/qcrbox-ghcr.env ]; then
    # shellcheck disable=SC1091
    . /run/qcrbox-ghcr.env
    rm -f /run/qcrbox-ghcr.env
fi
if { [ -n "$TLS_CERT" ] && [ -z "$TLS_KEY" ]; } || { [ -z "$TLS_CERT" ] && [ -n "$TLS_KEY" ]; }; then
    echo "ERROR: --tls-cert and --tls-key must be given together" >&2; exit 1
fi
if [ -n "$TLS_CERT" ] && [ -n "$ACME_EMAIL" ]; then
    echo "ERROR: --acme-email and --tls-cert are mutually exclusive" >&2; exit 1
fi

QCRBOX_DIR="$SOURCE_DIR/QCrBox"
FRONTEND_DIR="$SOURCE_DIR/QCrBoxFrontend"
[ -d "$QCRBOX_DIR" ] || { echo "ERROR: $QCRBOX_DIR not found" >&2; exit 1; }
[ -d "$FRONTEND_DIR" ] || { echo "ERROR: $FRONTEND_DIR not found" >&2; exit 1; }

if [ "$UPDATE" = true ]; then
    # In-place upgrade: keep secrets, accounts and data; only bump the image
    # version (and TLS material if new certificate flags are given).
    [ -f "$QCRBOX_DIR/.env.vm" ] || {
        echo "ERROR: --update requires an existing installation ($QCRBOX_DIR/.env.vm not found)." >&2
        echo "       Run without --update for a fresh install." >&2
        exit 1
    }
    [ -f "$FRONTEND_DIR/environment.env" ] || {
        echo "ERROR: --update requires the existing frontend environment ($FRONTEND_DIR/environment.env)." >&2
        exit 1
    }
    echo "==> Updating existing QCrBox installation for https://$DOMAIN (version: $VERSION)"
else
    echo "==> Provisioning QCrBox for https://$DOMAIN"
fi

# ---------------------------------------------------------------- docker ----
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing docker"
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
fi

# ------------------------------------------------------------ reroll secrets
if [ "$UPDATE" = false ]; then
    echo "==> Generating fresh secrets"
    AUTHELIA_JWT_SECRET=$(openssl rand -hex 32)
    AUTHELIA_SESSION_SECRET=$(openssl rand -hex 64)
    AUTHELIA_STORAGE_ENCRYPTION_KEY=$(openssl rand -hex 32)
    LLDAP_JWT_SECRET=$(openssl rand -hex 32)
    LLDAP_KEY_SEED=$(openssl rand -hex 32)
    DJANGO_SECRET_KEY=$(openssl rand -hex 50)
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    # Admin password for the LLDAP 'admin' user — used to log in at the Authelia
    # portal, to manage accounts at https://users.<domain>, and for /admin in
    # the frontend (Django superuser with the same name).
    ADMIN_PASSWORD=$(openssl rand -base64 18 | tr '+/' '-_')
fi

# --------------------------------------------------------------- TLS mode ---
TLS_CERT_RESOLVER=""
if [ -n "$ACME_EMAIL" ]; then
    TLS_CERT_RESOLVER="letsencrypt"
    echo "==> TLS: Let's Encrypt ($ACME_EMAIL)"
elif [ -n "$TLS_CERT" ]; then
    echo "==> TLS: supplied certificate"
    DYNAMIC_DIR="$QCRBOX_DIR/services/core/qcrbox_traefik/dynamic"
    install -m 644 "$TLS_CERT" "$DYNAMIC_DIR/qcrbox.crt"
    install -m 600 "$TLS_KEY" "$DYNAMIC_DIR/qcrbox.key"
    cat > "$DYNAMIC_DIR/tls.yml" <<'EOF'
tls:
  stores:
    default:
      defaultCertificate:
        certFile: /etc/traefik/dynamic/qcrbox.crt
        keyFile: /etc/traefik/dynamic/qcrbox.key
EOF
else
    echo "==> TLS: self-signed default certificate (browsers will warn)"
fi

# ------------------------------------------------------- QCrBox environment
if [ "$UPDATE" = true ]; then
    echo "==> Updating $QCRBOX_DIR/.env.vm (version only; secrets untouched)"
    sed -i \
        -e "s|^QCRBOX_DOCKER_TAG=.*|QCRBOX_DOCKER_TAG=$VERSION|" \
        "$QCRBOX_DIR/.env.vm"
    if [ -n "$ACME_EMAIL" ] || [ -n "$TLS_CERT" ]; then
        sed -i \
            -e "s|^QCRBOX_TLS_CERT_RESOLVER=.*|QCRBOX_TLS_CERT_RESOLVER=$TLS_CERT_RESOLVER|" \
            -e "s|^QCRBOX_ACME_EMAIL=.*|QCRBOX_ACME_EMAIL=$ACME_EMAIL|" \
            "$QCRBOX_DIR/.env.vm"
    fi
else
    echo "==> Writing $QCRBOX_DIR/.env.vm"
    cp "$QCRBOX_DIR/.env.prod" "$QCRBOX_DIR/.env.vm"
    sed -i \
        -e "s|^QCRBOX_DOCKER_TAG=.*|QCRBOX_DOCKER_TAG=$VERSION|" \
        -e "s|^QCRBOX_DOMAIN=.*|QCRBOX_DOMAIN=$DOMAIN|" \
        -e "s|^QCRBOX__REVERSE_PROXY__PORT=.*|QCRBOX__REVERSE_PROXY__PORT=80|" \
        -e "s|^QCRBOX_TLS_CERT_RESOLVER=.*|QCRBOX_TLS_CERT_RESOLVER=$TLS_CERT_RESOLVER|" \
        -e "s|^QCRBOX_ACME_EMAIL=.*|QCRBOX_ACME_EMAIL=$ACME_EMAIL|" \
        -e "s|^AUTHELIA_JWT_SECRET=.*|AUTHELIA_JWT_SECRET=$AUTHELIA_JWT_SECRET|" \
        -e "s|^AUTHELIA_SESSION_SECRET=.*|AUTHELIA_SESSION_SECRET=$AUTHELIA_SESSION_SECRET|" \
        -e "s|^AUTHELIA_STORAGE_ENCRYPTION_KEY=.*|AUTHELIA_STORAGE_ENCRYPTION_KEY=$AUTHELIA_STORAGE_ENCRYPTION_KEY|" \
        -e "s|^LLDAP_JWT_SECRET=.*|LLDAP_JWT_SECRET=$LLDAP_JWT_SECRET|" \
        -e "s|^LLDAP_KEY_SEED=.*|LLDAP_KEY_SEED=$LLDAP_KEY_SEED|" \
        -e "s|^LLDAP_ADMIN_PASSWORD=.*|LLDAP_ADMIN_PASSWORD=$ADMIN_PASSWORD|" \
        "$QCRBOX_DIR/.env.vm"
    if [ "$ON_DEMAND" = true ]; then
        sed -i -e "s|^QCRBOX__ORCHESTRATOR__ENABLED=.*|QCRBOX__ORCHESTRATOR__ENABLED=true|" \
            "$QCRBOX_DIR/.env.vm"
        cat >> "$QCRBOX_DIR/.env.vm" <<'EOF'

# Resource limits for on-demand app containers (added by provision_qcrbox.sh;
# adjust to the server's hardware, empty = unlimited).
QCRBOX__ORCHESTRATOR__CONTAINER_MEMORY_LIMIT_MB=8192
QCRBOX__ORCHESTRATOR__CONTAINER_CPU_LIMIT=4
QCRBOX__ORCHESTRATOR__MAX_TOTAL_INSTANCES=10
EOF
    fi
fi
chmod 600 "$QCRBOX_DIR/.env.vm"

# ----------------------------------------------------- frontend environment
if [ "$UPDATE" = true ]; then
    echo "==> Keeping existing frontend environment"
else
echo "==> Writing frontend environment"
cat > "$FRONTEND_DIR/.env" <<EOF
# docker-compose substitution variables (generated by provision_qcrbox.sh)
QCRBOX_DOMAIN=$DOMAIN
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
EOF
chmod 600 "$FRONTEND_DIR/.env"

cat > "$FRONTEND_DIR/environment.env" <<EOF
# Generated by provision_qcrbox.sh
DEBUG=False

DJANGO_SECRET_KEY='$DJANGO_SECRET_KEY'

DJANGO_DB='postgresql'
POSTGRES_HOST='db'
POSTGRES_NAME='postgres'
POSTGRES_USER='postgres'
POSTGRES_PASSWORD='$POSTGRES_PASSWORD'
POSTGRES_PORT=5432

API_BASE_URL='http://qcrbox-registry:8000'

QCRBOX_DOMAIN='$DOMAIN'
ALLOWED_HOSTS='$DOMAIN'
CSRF_TRUSTED_ORIGINS='https://$DOMAIN'

AUTHELIA_SSO=True
AUTHELIA_LOGOUT_URL='https://auth.$DOMAIN/logout'

TRAEFIK_HTTP_PORT=''
GUI_DOMAIN_PREFIX='.gui.'

MAX_LENGTH_API_LOG=10000

# Django superuser, matched by username to the Authelia 'admin' user, so the
# SSO admin has access to the Django admin interface as well.
DJANGO_SUPERUSER_EMAIL=admin@$DOMAIN
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD='$ADMIN_PASSWORD'
EOF
chmod 600 "$FRONTEND_DIR/environment.env"
fi

# ------------------------------------------------------------ start backend
if [ "$UPDATE" = false ]; then
    # Stop any previous deployment first: rerolled secrets invalidate the
    # Authelia, LLDAP and Postgres state (postgres only applies its password on
    # first initialisation), and volumes can only be removed when unused.
    # (--update skips this wipe: accounts, TOTP state and frontend data survive.)
    docker compose --project-name qcrboxfrontend down --remove-orphans >/dev/null 2>&1 || true
    docker compose --project-name qcrbox down --remove-orphans >/dev/null 2>&1 || true
    docker volume rm -f qcrbox_qcrbox-authelia-data qcrbox_qcrbox-lldap-data \
        qcrboxfrontend_postgres_data >/dev/null 2>&1 || true
fi

COMPOSE=(docker compose --project-name qcrbox
         --env-file "$QCRBOX_DIR/.env.vm"
         -f "$QCRBOX_DIR/docker-compose.prebuilt.yml")
for app in $APPS; do
    # Accept any separator variant: exact name, then hyphens→underscores,
    # then underscores→hyphens, so callers can use either form.
    app_dir="$QCRBOX_DIR/services/applications/$app"
    [ -d "$app_dir" ] || app_dir="$QCRBOX_DIR/services/applications/${app//-/_}"
    [ -d "$app_dir" ] || app_dir="$QCRBOX_DIR/services/applications/${app//_/-}"
    app_compose=$(ls "$app_dir"/docker-compose.*.prebuilt.yml 2>/dev/null | head -1)
    [ -n "$app_compose" ] || { echo "ERROR: no prebuilt compose file for app '$app'" >&2; exit 1; }
    COMPOSE+=(-f "$app_compose")
done

if [[ -n "$GHCR_TOKEN" ]]; then
    echo "==> Authenticating with GHCR"
    echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:-token}" --password-stdin
fi

echo "==> Pulling backend images from GHCR"
# Non-fatal: on machines without registry access, pre-loaded images
# (docker load) of the right version are used instead.
"${COMPOSE[@]}" pull \
    || echo "WARNING: image pull failed; continuing with locally available images"

echo "==> Starting QCrBox backend (apps: ${APPS:-none})"
"${COMPOSE[@]}" up -d --no-build

echo "==> Waiting for backend health"
timeout 300 bash -c 'until [ "$(docker ps --filter health=starting -q | wc -l)" -eq 0 ]; do sleep 5; done'
docker ps --format 'table {{.Names}}\t{{.Status}}'
[ "$(docker ps --filter health=unhealthy -q | wc -l)" -eq 0 ] || {
    echo "ERROR: some containers are unhealthy" >&2; exit 1; }

# ----------------------------------------------------------- start frontend
FRONTEND_REPO=$(grep -m1 '^QCRBOX_DOCKER_REPO=' "$QCRBOX_DIR/.env.vm" | cut -d= -f2)
FRONTEND_IMG="$FRONTEND_REPO/qcrboxfrontend-server:$VERSION"
echo "==> Pulling frontend image $FRONTEND_IMG"
docker pull "$FRONTEND_IMG" \
    || echo "WARNING: frontend image pull failed; continuing with a locally available image"
docker image inspect "$FRONTEND_IMG" >/dev/null 2>&1 \
    || { echo "ERROR: frontend image $FRONTEND_IMG is not available (pull failed and not pre-loaded)" >&2; exit 1; }
docker tag "$FRONTEND_IMG" qcrboxfrontend-server:latest

echo "==> Starting frontend"
docker compose --project-name qcrboxfrontend \
    -f "$FRONTEND_DIR/docker-compose.yml" --project-directory "$FRONTEND_DIR" \
    up -d --no-build

# ------------------------------------------------------------- credentials
CRED_FILE=/root/qcrbox-credentials.txt
if [ "$UPDATE" = false ]; then
cat > "$CRED_FILE" <<EOF
QCrBox installation credentials ($(date -u +%Y-%m-%dT%H:%M:%SZ))
Domain: $DOMAIN

Web login (Authelia portal; also user management at https://users.$DOMAIN
and the Django admin):
  username: admin
  password: $ADMIN_PASSWORD

Create further accounts at https://users.$DOMAIN (LLDAP web UI).

Internal secrets (recorded for disaster recovery; not needed day-to-day):
  AUTHELIA_JWT_SECRET=$AUTHELIA_JWT_SECRET
  AUTHELIA_SESSION_SECRET=$AUTHELIA_SESSION_SECRET
  AUTHELIA_STORAGE_ENCRYPTION_KEY=$AUTHELIA_STORAGE_ENCRYPTION_KEY
  LLDAP_JWT_SECRET=$LLDAP_JWT_SECRET
  LLDAP_KEY_SEED=$LLDAP_KEY_SEED
  DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
  POSTGRES_PASSWORD=$POSTGRES_PASSWORD
EOF
chmod 600 "$CRED_FILE"
fi

echo ""
if [ "$UPDATE" = true ]; then
    echo "==> Update complete (version: $VERSION). Accounts, data and secrets unchanged."
else
    echo "==> Done. Credentials saved to $CRED_FILE"
fi
echo ""
echo "    Frontend:   https://$DOMAIN"
echo "    Auth:       https://auth.$DOMAIN"
echo "    Users:      https://users.$DOMAIN"
echo "    API:        https://api.registry.$DOMAIN"
echo "    Dashboard:  https://traefik.$DOMAIN"
for app in $APPS; do
    slug=$(echo "$app" | tr '_' '-')
    echo "    GUI:        https://$slug.gui.$DOMAIN (router slug may differ per app)"
done
if [ "$UPDATE" = false ]; then
    echo ""
    echo "    Login: admin / $ADMIN_PASSWORD"
fi
