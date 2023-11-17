#!/usr/bin/env bash

set -euo pipefail

echo "[DDD] QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}"

chown -R --dereference -L ${APP_USER}:${APP_USER} ${APP_HOME} ${QCRBOX_ROOT_DIR} /tmp /dev/stdout
gosu ${APP_USER} supervisord
exec gosu ${APP_USER} "$@"
