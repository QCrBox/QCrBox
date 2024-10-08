# This script is intended to be sourced from the devbox shell.
# It sets up the shell environment, such as aliases and
# platform-specific environment variables.

function main() {
    source ./scripts/devbox/set_aliases.sh
    source ./scripts/devbox/set_platform_agnostic_env_vars.sh
    source ./scripts/devbox/set_platform_specific_env_vars.sh
}

main
