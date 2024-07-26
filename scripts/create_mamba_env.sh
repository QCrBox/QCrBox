set -euo pipefail

SCRIPT_DIR=$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)
QCRBOX_ROOT=$(readlink -f $SCRIPT_DIR/..)

echo "[DDD] SCRIPT_DIR=${SCRIPT_DIR}"
echo "[DDD] QCRBOX_ROOT=${QCRBOX_ROOT}"
echo "[DDD] MAMBA_ROOT_PREFIX=${MAMBA_ROOT_PREFIX}"

mkdir -p ${MAMBA_ROOT_PREFIX}

if ! [ -e ${MAMBA_ROOT_PREFIX}/.mambarc ]; then
    cp ${QCRBOX_ROOT}/services/base_images/base_ancestor/mambarc ${MAMBA_ROOT_PREFIX}/.mambarc;
fi

if ! [ -e ${QCRBOX_MAMBA_ENV_PATH} ]; then
    echo "Creating qcrbox mamba environment...";
    eval "$(micromamba shell hook --shell bash)";
    micromamba create -n qcrbox;
    micromamba activate qcrbox;
    micromamba install -y python=3.12;
    micromamba install -y pip setuptools wheel build conda-build;
    micromamba install -y cctbx-base;

    #micromamba clean -y --all --force-pkgs-dirs;
fi
