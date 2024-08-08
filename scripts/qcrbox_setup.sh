#!/usr/bin/env bash

set -euo pipefail

readonly PROGNAME=$(basename $0)
readonly CUR_WORK_DIR=$(pwd)
readonly ARGS="$*"

_TARGET_DIR="${CUR_WORK_DIR}/QCrBox"
_DRY_RUN="false"
_FOUND_NIX="false"
_FOUND_DEVBOX="false"
_FOUND_DOCKER="false"


usage() {
    >&2	cat <<- EOF
	Usage: $PROGNAME OPTIONS

	Set up a development environment for QCrBox.

	OPTIONS:
	   -t --target-dir          Target directory for cloning the QCrBox repository. The
	                            repo will be cloned into a subfolder called 'QCrBox'
	                            of this directory, and the development environment will
	                            be set up inside this subfolder. Default is the current
	                            directory.
	   -n --dry-run             Only show the actions that would be performed, without
	                            making any changes.
	   -h --help                Show this help.
	EOF
}


print_heading() {
    echo "QCrBox Development Environment Setup"
    echo
}


abort_if_qcrbox_repo_exists() {
    local qcrbox_repo_path=${_TARGET_DIR}

    if [[ -e ${qcrbox_repo_path} ]] &&
       [[ -n "$(ls -A ${qcrbox_repo_path})" ]]; then
	      echo "Error: destination path '${qcrbox_repo_path}' already exists and is not an empty directory."
	      echo
	      echo "Please remove this directory or use -t/--target-dir to choose a different location."
	      exit 1
    fi
}

check_for_command() {
  local cmd_name=$1
  local version_flag=$2

  if command -v ${cmd_name} > /dev/null; then
    echo "✔ Found ${cmd_name}: $(${cmd_name} ${version_flag})"
    return 0
  else
    echo "⚠️  Command not found: '${cmd_name}'"
    return 1
  fi
}


check_prerequisites() {
    echo "Checking prerequisites..."
    sleep 0.5
    echo
    check_for_command nix --version \
        && _FOUND_NIX="true" \
        || _FOUND_NIX="false"
    check_for_command devbox version \
        && _FOUND_DEVBOX="true" \
        || _FOUND_DEVBOX="false"
    check_for_command docker --version \
        || print_docker_installation_hint
    echo
}


print_docker_installation_hint() {
    cat <<- EOF

	   Warning: Docker could not be found.

	   This script can proceed without it, but docker is required
	   in order to build and run the QCrBox containers once the
	   development environment has been set up.

	   Please install Docker Desktop by following the instructions
	   for your operating system here:

	       https://docs.docker.com/desktop/
	EOF
}


clear_screen() {
    printf "\033[H\033[2J"
}

install_git_in_temporary_devbox_environment() {
    local devbox_tmpdir=$1

    echo "Installing git in a temporary devbox environment..."
    pushd ${devbox_tmpdir} > /dev/null
    devbox init
    devbox add git
    devbox install -q
    popd > /dev/null
    echo "Done."
}


clone_qcrbox_repo_into_target_directory() {
    local devbox_tmpdir=$1
    local qcrbox_target_repo_path=$2
    local git_revision=$3

    echo "Cloning QCrBox repository into ${qcrbox_target_repo_path}"
    devbox run -c ${devbox_tmpdir} "git clone https://github.com/QCrBox/QCrBox.git ${qcrbox_target_repo_path}"
    echo "Checking out git branch/revision: ${git_revision}"
    devbox run -c ${devbox_tmpdir} "cd ${qcrbox_target_repo_path} && git checkout ${git_revision}"
}


delete_devbox_tmpdir() {
    local devbox_tmpdir=$1

    echo "Deleting temporary devbox environment in ${devbox_tmpdir}"
    rm -rf ${devbox_tmpdir}
}


install_git_and_clone_qcrbox_repo() {
    local qcrbox_target_repo_path=$1
    local git_revision=$2
    local devbox_tmpdir

    devbox_tmpdir=$(mktemp -d 2>/dev/null || mktemp -d -t 'tmpdir')
    install_git_in_temporary_devbox_environment ${devbox_tmpdir}
    clone_qcrbox_repo_into_target_directory ${devbox_tmpdir} ${qcrbox_target_repo_path} ${git_revision}
    delete_devbox_tmpdir ${devbox_tmpdir}
}


install_qcrbox_devbox_environment() {
    local qcrbox_repo_path=$1

    echo "Installing QCrBox development environment"
    devbox install -c ${qcrbox_repo_path}

    cat <<- EOF

	Successfully installed development environment for QCrBox.

	Next steps:

	* Change into the cloned QCrBox repository:

	     $ cd ${qcrbox_repo_path}

	* Activate the devbox shell (automatically installs the QCrBox dependencies into it):

	     $ devbox shell

	* Run the 'qcb' command to verify that the installation worked as expected, for example:

	     $ qcb
	     $ qcb version
	EOF
}


print_planned_actions() {
    echo "Planned actions:"
    [[ "${_FOUND_NIX}" == "false" ]] \
        && echo "* Install Nix using the Determinate Systems Nix Installer (https://github.com/DeterminateSystems/nix-installer)"
    [[ "${_FOUND_DEVBOX}" == "false" ]] \
        && echo "* Install Devbox (https://www.jetify.com/devbox/docs/)"
    echo

    echo "* Clone the QCrBox repository into target directory: ${_TARGET_DIR}"
    echo "  (Use the --target-dir option to choose a different location.)"
    echo "* Install a devbox environment with all dependencies inside the cloned repository"
    echo
}


quit_if_dry_run() {
    if [[ "${_DRY_RUN}" == "true" ]]; then
        echo "This script was executed in 'dry-run' mode. No changes were made."
        exit 0
    fi
}


prompt_for_confirmation() {
    local answer
    #read -p "Proceed? ([Y]es/[n]o/[e]xplain): " answer
    read -p "Proceed? ([Y]es/[n]o): " answer
    case ${answer} in
        y|Y|"" )
            echo "Proceeding with installation"
            ;;
#        e|E)
#            echo "Here is a detailed explanation:"
#            exit 0
#            ;;
        n|N|*)
            echo "Exiting installation."
            exit 0
            ;;
    esac
}

install_nix_if_needed() {
    if [[ "${_FOUND_NIX}" == "true" ]]; then
        return
    fi

    echo
    echo "We recommend installing Nix using the Determinate Systems Nix Installer."
    echo "I can do this automatically for you, or you can follow the instructions"
    echo "here: https://github.com/DeterminateSystems/nix-installer"
    echo
    read -p "Would you like me to install Nix for you now? [Y/n] " answer
    case ${answer:0:1} in
        y|Y|"" )
            curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
	    echo
        ;;
        * )
            echo "Exiting installation."
	    exit 0
        ;;
    esac
}


install_devbox_if_needed() {
    if [[ "${_FOUND_DEVBOX}" == "true" ]]; then
        return
    fi

    echo
    echo "You can install Devbox by following the instructions here: https://www.jetify.com/devbox/docs/installing_devbox/"
    echo "Alternatively, I can do this for you automatically."
    echo
    read -p "Would you like me to install Devbox for you now? [Y/n] " answer
    case ${answer:0:1} in
        y|Y|"" )
            curl -fsSL https://get.jetify.com/devbox | bash
	    echo
        ;;
        * )
            echo "Exiting installation."
	    exit 0
        ;;
    esac
}



cmdline() {
    local args=""
    local arg
    for arg
    do
        local delim=""
        case "$arg" in
            # Translate --gnu-long-options to -g (short options)
            --target-dir)        args="${args}-t ";;
            --dry-run)           args="${args}-n ";;
            --help)              args="${args}-h ";;
            *)
                # Print error in case of invalid long options
                if [[ "${arg:0:2}" == "--" ]]; then
                    >&2 echo "Unrecognized option: ${arg}"
                    >&2 echo
                    usage
                    exit 1
                fi
                # Pass through anything else
                [[ "${arg:0:1}" == "-" ]] || delim="\""
                args="${args}${delim}${arg}${delim} "
                ;;
        esac
    done

    # Reset the positional parameters to the short options
    eval set -- $args

    while getopts ":t::nh" option 2>/dev/null
    do
        case $option in
            t)
                _TARGET_DIR=${OPTARG}
                ;;
            n)
                _DRY_RUN="true"
                ;;
            h)
                usage
                exit 0
                ;;
            *)
                >&2 echo "Unrecognized option: -${OPTARG}"
                >&2 echo
                usage
                exit 1
                ;;
        esac
    done

    local qcrbox_repo_path=${_TARGET_DIR}
    local git_revision="dev"

    # Pre-flight check
    clear_screen
    print_heading
    abort_if_qcrbox_repo_exists
    check_prerequisites
    print_planned_actions
    quit_if_dry_run
    prompt_for_confirmation

    # Run installation
    install_nix_if_needed
    install_devbox_if_needed
    install_git_and_clone_qcrbox_repo ${qcrbox_repo_path} ${git_revision}
    install_qcrbox_devbox_environment ${qcrbox_repo_path}
}


main() {
  cmdline $ARGS
}
main
