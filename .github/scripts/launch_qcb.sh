#!/bin/bash

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <QCrBox directory>"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "Error: '$1' is not a valid directory."
    exit 1
fi

cd "$1" || exit 1

echo "Installing Python dependencies for QCrBox"
pip install --upgrade uv
uv pip install --system -r ./pyqcrbox/requirements-dev.txt
uv pip install --system pyqcrbox@./pyqcrbox

echo "Brining up QCrBox registry and test applications"
qcb down
docker system prune -af
qcb up --test-only

bash .github/scripts/check_qcb_healthy.sh $1
