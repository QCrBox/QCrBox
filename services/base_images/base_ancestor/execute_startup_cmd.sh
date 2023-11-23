#!/usr/bin/env bash

set -euo pipefail

if [ -z "$1" ]; then
  echo "No arguments supplied to 'execute_startup_cmd.sh'. Nothing to do here."
else
  echo "Executing startup command in new shell: $@"
  bash -c "$@"
  echo "Startup command finished. Killing supervisord to exit the container."
  pkill supervisord
fi
