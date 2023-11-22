#!/usr/bin/env bash

set -euo pipefail

# Set env var QCRBOX_CMD_ARGS, which will be picked up by the
# script `execute_startup_cmd.sh` (which is run by supervisor).
export QCRBOX_CMD_ARGS="$@"

exec supervisord
