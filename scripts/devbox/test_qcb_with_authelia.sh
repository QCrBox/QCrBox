#!/usr/bin/env bash
# Test script to verify qcb commands work with Authelia authentication setup

set -euo pipefail

echo "🔍 Testing QCrBox with Authelia Authentication Setup"
echo "=================================================="
echo ""

# Check if we're in devbox shell
if [ -z "$DEVBOX_SHELL_ENABLED" ]; then
    echo "⚠️  Not in devbox shell. Run 'devbox shell' first."
    echo ""
    echo "To test:"
    echo "  1. Run: devbox shell"
    echo "  2. Run: bash scripts/devbox/test_qcb_with_authelia.sh"
    exit 1
fi

echo "✓ Running in devbox shell"
echo ""

# Check if qcb command is available
if ! command -v qcb &> /dev/null; then
    echo "❌ qcb command not found"
    echo "   Run 'uv pip install -e ./pyqcrbox' in devbox shell"
    exit 1
fi

echo "✓ qcb command is available"
echo ""

# Check environment variables
echo "📋 Checking environment variables in .env.dev:"
echo ""

if ! grep -q "^QCRBOX_DOMAIN=" .env.dev; then
    echo "❌ QCRBOX_DOMAIN not found in .env.dev"
    exit 1
fi
echo "✓ QCRBOX_DOMAIN=$(grep "^QCRBOX_DOMAIN=" .env.dev | cut -d= -f2)"

if ! grep -q "^AUTHELIA_JWT_SECRET=" .env.dev; then
    echo "❌ AUTHELIA_JWT_SECRET not found in .env.dev"
    exit 1
fi
echo "✓ AUTHELIA_JWT_SECRET is set"

if ! grep -q "^AUTHELIA_SESSION_SECRET=" .env.dev; then
    echo "❌ AUTHELIA_SESSION_SECRET not found in .env.dev"
    exit 1
fi
echo "✓ AUTHELIA_SESSION_SECRET is set"

if ! grep -q "^AUTHELIA_STORAGE_ENCRYPTION_KEY=" .env.dev; then
    echo "❌ AUTHELIA_STORAGE_ENCRYPTION_KEY not found in .env.dev"
    exit 1
fi
echo "✓ AUTHELIA_STORAGE_ENCRYPTION_KEY is set"

for var in LLDAP_JWT_SECRET LLDAP_KEY_SEED LLDAP_ADMIN_PASSWORD; do
    if ! grep -q "^${var}=" .env.dev; then
        echo "❌ ${var} not found in .env.dev"
        exit 1
    fi
    echo "✓ ${var} is set"
done
echo ""

# Check if Authelia config files exist
echo "📁 Checking Authelia configuration files:"
echo ""

if [ ! -f "services/core/qcrbox_auth/authelia_config.yml" ]; then
    echo "❌ services/core/qcrbox_auth/authelia_config.yml not found"
    exit 1
fi
echo "✓ authelia_config.yml exists"

if ! grep -q "implementation: lldap" services/core/qcrbox_auth/authelia_config.yml; then
    echo "❌ authelia_config.yml does not use the LLDAP authentication backend"
    exit 1
fi
echo "✓ authelia_config.yml uses the LLDAP backend"
echo ""

# Test docker compose config generation
echo "🐳 Testing docker compose configuration:"
echo ""

if ! docker compose -f docker-compose.run.yml --env-file .env.dev config > /dev/null 2>&1; then
    echo "❌ docker-compose.run.yml configuration is invalid"
    docker compose -f docker-compose.run.yml --env-file .env.dev config 2>&1 | head -20
    exit 1
fi
echo "✓ docker-compose.run.yml is valid"

if ! docker compose -f docker-compose.prebuilt.yml --env-file .env.dev config > /dev/null 2>&1; then
    echo "❌ docker-compose.prebuilt.yml configuration is invalid"
    docker compose -f docker-compose.prebuilt.yml --env-file .env.dev config 2>&1 | head -20
    exit 1
fi
echo "✓ docker-compose.prebuilt.yml is valid"
echo ""

# Check if qcrbox-authelia service is defined
echo "🔐 Checking Authelia service definition:"
echo ""

if ! docker compose -f docker-compose.run.yml --env-file .env.dev config 2>/dev/null | grep -q "qcrbox-authelia:"; then
    echo "❌ qcrbox-authelia service not found in docker-compose.run.yml"
    exit 1
fi
echo "✓ qcrbox-authelia service is defined"

if ! docker compose -f docker-compose.run.yml --env-file .env.dev config 2>/dev/null | grep -q "qcrbox-lldap:"; then
    echo "❌ qcrbox-lldap service not found in docker-compose.run.yml"
    exit 1
fi
echo "✓ qcrbox-lldap service is defined"

# Check if registry has Traefik labels
if ! docker compose -f docker-compose.run.yml --env-file .env.dev config 2>/dev/null | grep -q "traefik.http.routers.registry-api"; then
    echo "❌ Registry Traefik routing not configured"
    exit 1
fi
echo "✓ Registry has Traefik routing configured"

# Check if ForwardAuth middleware is defined
if ! docker compose -f docker-compose.run.yml --env-file .env.dev config 2>/dev/null | grep -q "authelia-auth.forwardauth"; then
    echo "❌ Authelia ForwardAuth middleware not configured"
    exit 1
fi
echo "✓ Authelia ForwardAuth middleware is configured"
echo ""

# Check that every application router is protected by the ForwardAuth middleware
echo "🖥️  Checking that GUI application routers require authentication:"
echo ""

unprotected=0
for compose_file in services/applications/*/docker-compose.*.run.yml services/applications/*/docker-compose.*.prebuilt.yml; do
    [ -f "$compose_file" ] || continue
    grep -q "traefik.enable" "$compose_file" || continue
    for router in $(grep -oP 'traefik\.http\.routers\.\K[^.]+(?=\.rule:)' "$compose_file" | sort -u); do
        if ! grep -q "traefik.http.routers.${router}.middlewares: authelia-auth" "$compose_file"; then
            echo "❌ Router '${router}' in ${compose_file} lacks the authelia-auth middleware"
            unprotected=1
        fi
        if ! grep -q "traefik.http.routers.${router}.entrypoints: websecure" "$compose_file"; then
            echo "❌ Router '${router}' in ${compose_file} is not restricted to the websecure entrypoint"
            unprotected=1
        fi
    done
done
if [ "$unprotected" -ne 0 ]; then
    exit 1
fi
echo "✓ All application routers use authelia-auth and the websecure entrypoint"
echo ""

echo "✅ All checks passed!"
echo ""
echo "📚 Next steps:"
echo "  1. Start services: qcb up --all"
echo "  2. Access registry API at: https://api.registry.qcrbox.localhost"
echo "  3. Login at: https://auth.qcrbox.localhost"
echo "     Username: admin"
echo "     Password: changeme"
echo ""
echo "📖 See docs/how_to_guides/setup_authelia_authentication.md for more information"
