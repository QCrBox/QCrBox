#!/usr/bin/env bash
#
# Provision a fresh Ubuntu VM (or server) with the full QCrBox stack:
# backend (Traefik + Authelia + registry + applications) and the web frontend,
# with every secret freshly generated ("rerolled") for this installation.
#
# This script runs INSIDE the target machine as root (or via sudo). It expects
# the source trees at <source>/QCrBox and <source>/QCrBoxFrontend and the
# docker images either preloaded (see deploy_qcrbox_ssh.sh) or buildable.
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
#       [--acme-email you@example.org | --tls-cert cert.pem --tls-key key.pem]
#
# Secrets are written to /root/qcrbox-credentials.txt (mode 600).

set -euo pipefail

DOMAIN=""
SOURCE_DIR="/opt/qcrbox-src"
APPS=""
ACME_EMAIL=""
TLS_CERT=""
TLS_KEY=""

while [ $# -gt 0 ]; do
    case "$1" in
        --domain)     DOMAIN="$2"; shift 2 ;;
        --source)     SOURCE_DIR="$2"; shift 2 ;;
        --apps)       APPS="$2"; shift 2 ;;
        --acme-email) ACME_EMAIL="$2"; shift 2 ;;
        --tls-cert)   TLS_CERT="$2"; shift 2 ;;
        --tls-key)    TLS_KEY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

[ -n "$DOMAIN" ] || { echo "ERROR: --domain is required" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run as root (sudo)" >&2; exit 1; }
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

echo "==> Provisioning QCrBox for https://$DOMAIN"

# ---------------------------------------------------------------- docker ----
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing docker"
    curl -fsSL https://get.docker.com | sh
fi

# ------------------------------------------------------------ reroll secrets
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
echo "==> Writing $QCRBOX_DIR/.env.vm"
cp "$QCRBOX_DIR/.env.dev" "$QCRBOX_DIR/.env.vm"
sed -i \
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
chmod 600 "$QCRBOX_DIR/.env.vm"

# ----------------------------------------------------- frontend environment
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

# ------------------------------------------------------------ start backend
# Stop any previous deployment first: rerolled secrets invalidate the
# Authelia, LLDAP and Postgres state (postgres only applies its password on
# first initialisation), and volumes can only be removed when unused.
docker compose --project-name qcrboxfrontend down --remove-orphans >/dev/null 2>&1 || true
docker compose --project-name qcrbox down --remove-orphans >/dev/null 2>&1 || true
docker volume rm -f qcrbox_qcrbox-authelia-data qcrbox_qcrbox-lldap-data \
    qcrboxfrontend_postgres_data >/dev/null 2>&1 || true

COMPOSE=(docker compose --project-name qcrbox
         --env-file "$QCRBOX_DIR/.env.vm"
         -f "$QCRBOX_DIR/docker-compose.run.yml")
for app in $APPS; do
    app_compose=$(ls "$QCRBOX_DIR/services/applications/$app"/docker-compose.*.run.yml 2>/dev/null | head -1)
    [ -n "$app_compose" ] || { echo "ERROR: no run compose file for app '$app'" >&2; exit 1; }
    COMPOSE+=(-f "$app_compose")
done

echo "==> Starting QCrBox backend (apps: ${APPS:-none})"
"${COMPOSE[@]}" up -d --no-build

echo "==> Waiting for backend health"
for _ in $(seq 1 60); do
    starting=$(docker ps --filter health=starting -q | wc -l)
    [ "$starting" -eq 0 ] && break
    sleep 5
done
docker ps --format 'table {{.Names}}\t{{.Status}}'
[ "$(docker ps --filter health=unhealthy -q | wc -l)" -eq 0 ] || {
    echo "ERROR: some containers are unhealthy" >&2; exit 1; }

# ----------------------------------------------------------- start frontend
echo "==> Starting frontend"
if docker image inspect qcrboxfrontend-server >/dev/null 2>&1; then
    docker compose --project-name qcrboxfrontend \
        -f "$FRONTEND_DIR/docker-compose.yml" --project-directory "$FRONTEND_DIR" \
        up -d --no-build
else
    docker compose --project-name qcrboxfrontend \
        -f "$FRONTEND_DIR/docker-compose.yml" --project-directory "$FRONTEND_DIR" \
        up -d --build
fi

# ------------------------------------------------------------- credentials
CRED_FILE=/root/qcrbox-credentials.txt
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

echo ""
echo "==> Done. Credentials saved to $CRED_FILE"
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
echo ""
echo "    Login: admin / $ADMIN_PASSWORD"
