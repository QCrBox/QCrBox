function is_running_under_wsl() {
    # See: https://superuser.com/questions/1749781/how-can-i-check-if-the-environment-is-wsl-from-a-shell-script
    #
    local wsl_sentinel_file="/proc/sys/fs/binfmt_misc/WSLInterop"

    if [ -e ${wsl_sentinel_file} ]; then
        echo "Detected platform: Windows (WSL, distro: $WSL_DISTRO_NAME)"
        return 0
    else
        return 1
    fi
}

function is_running_under_darwin() {
    if [[ "$(uname -s)" == "Darwin" ]]; then
        echo "Detected platform: Darwin"
        return 0
    else
        return 1
    fi
}

function is_running_under_linux() {
    if [[ "$(uname -s)" == "Linux" ]]; then
        echo "Detected platform: Linux"
        return 0
    else
        return 1
    fi
}

function main() {
    local devbox_scripts_dir;

    devbox_scripts_dir="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

    if is_running_under_wsl; then
        source ${devbox_scripts_dir}/set_env_vars_windows_wsl.sh
    elif is_running_under_darwin; then
        source ${devbox_scripts_dir}/set_env_vars_darwin.sh
    elif is_running_under_linux; then
        source ${devbox_scripts_dir}/set_env_vars_linux.sh
    else
        echo "Unknown platform. Please open an issue at https://github.com/QCrBox/QCrBox/issues"
        exit 1
    fi
}

main
