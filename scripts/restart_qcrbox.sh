#!/bin/bash

set -euo pipefail

if [ -z "${DEVBOX_SHELL_ENABLED:-}" ]; then
    echo "Error: This script must be run inside a 'devbox shell' environment."
    echo "Please cd in /home/qcrbox/QCrBox and execute 'devbox shell' first."
    exit 1
fi

cd "${HOME}/QCrBox" || {
    echo "Failed to navigate into QCrBox repository"
    exit 1
}

echo "Restarting QCrBox registry and application containers"

# We'll bring everything down and back up again. We'll prune
# the containers, but keep volumes so we don't go out of sync
# with datasets in the frontend database
qcb down
docker system prune -f
qcb up --all

# We'll just sleep to make sure things have started up
sleep 10

# Check that the API is functional
if ! curl -s http://127.0.0.1:11000/api/healthz | jq -e '.status == "ok"' > /dev/null; then
    echo "QCrBox registry is not healthy."
    exit 1
fi

echo "QCrBox registry and application containers restarted successfully"
