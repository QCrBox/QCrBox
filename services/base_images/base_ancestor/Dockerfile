FROM mambaorg/micromamba:1.5.3-bullseye
SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update -y && \
    apt-get install -y --fix-missing --no-install-recommends \
        supervisor nano curl file iputils-ping wget rsync git \
        gosu htop less ncdu procps psmisc tmux tree vim \
        tar cabextract gzip bzip2 zip unzip xzip xz-utils \
        gcc make bash-completion locales \
        openssh-client ca-certificates && \
    rm -rf /var/lib/apt/lists

ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ARG QCRBOX_HOME=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
ONBUILD ARG QCRBOX_HOME=${QCRBOX_HOME}
ONBUILD ENV QCRBOX_HOME=${QCRBOX_HOME}

ARG QCRBOX_VOLUMES_ROOT_DIR

##
## Create user 'qcrbox'
##
ARG QCRBOX_USER=qcrbox
ARG QCRBOX_GROUP=${QCRBOX_USER}
ARG QCRBOX_HOME=${QCRBOX_ROOT_DIR}
ARG QCRBOX_USER_UID=1000
ARG QCRBOX_USER_GID=1000

RUN groupadd --gid ${QCRBOX_USER_GID} ${QCRBOX_GROUP} && \
    useradd --home-dir ${QCRBOX_HOME} --shell /bin/bash --uid ${QCRBOX_USER_UID} --gid ${QCRBOX_USER_GID} ${QCRBOX_USER} && \
    install -d -m 0755 -o ${QCRBOX_USER} -g ${QCRBOX_GROUP} ${QCRBOX_HOME}

ENV QCRBOX_USER=${QCRBOX_USER}
ENV QCRBOX_HOME=${QCRBOX_HOME}

##
## Create 'global' file /etc/supervisord.conf. Among other things, this includes any config files
## present in QCRBOX_SUPERVISORD_CONF_DIR (which is where QCrBox services will put them).
##
ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
ENV QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
COPY supervisord.conf /etc/supervisord.conf
RUN rm -f /etc/supervisor/supervisord.conf && \
    install -d -m 0755 -o ${QCRBOX_USER} -g ${QCRBOX_GROUP} \
        ${QCRBOX_SUPERVISORD_CONF_DIR} \
        ${QCRBOX_VOLUMES_ROOT_DIR}

USER ${QCRBOX_USER}
WORKDIR ${QCRBOX_HOME}

ARG MAMBA_EXE=micromamba
ARG MAMBA_ROOT_PREFIX=/opt/conda
ARG QCRBOX_MAMBA_ENV_NAME=qcrbox
ARG QCRBOX_MAMBA_ENV_PATH=${MAMBA_ROOT_PREFIX}/envs/${QCRBOX_MAMBA_ENV_NAME}
COPY mambarc ${MAMBA_ROOT_PREFIX}/.mambarc
RUN eval "$(micromamba shell hook --shell bash)" && \
    ${MAMBA_EXE} create -n ${QCRBOX_MAMBA_ENV_NAME} && \
    ${MAMBA_EXE} activate ${QCRBOX_MAMBA_ENV_NAME} && \
    ${MAMBA_EXE} install -y python=3.11 && \
    ${MAMBA_EXE} install -y pip setuptools wheel conda-build && \
    ${MAMBA_EXE} install -y cctbx-base && \
    ${MAMBA_EXE} clean -y --all --force-pkgs-dirs

##
## Create python virtual environment for QCrBox and install the `pyqcrbox` package into it
##
ARG QCRBOX_PYTHON_VENV_DIR=${QCRBOX_MAMBA_ENV_PATH}
ENV QCRBOX_PYTHON_VENV_DIR=${QCRBOX_PYTHON_VENV_DIR}

COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./pyqcrbox_dist/requirements.txt ./pyqcrbox_dist/requirements-server.txt ${QCRBOX_HOME}
RUN ${QCRBOX_PYTHON_VENV_DIR}/bin/python -m pip install -r ${QCRBOX_HOME}/requirements.txt -r ${QCRBOX_HOME}/requirements-server.txt

ARG QCRBOXTOOLS_VERSION
ARG QCRBOXTOOLS_WHEEL=qcrboxtools-${QCRBOXTOOLS_VERSION}-py3-none-any.whl
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./pyqcrbox_dist/${QCRBOXTOOLS_WHEEL} ${QCRBOX_HOME}/
RUN eval "$(micromamba shell hook --shell bash)" && \
    ${MAMBA_EXE} activate ${QCRBOX_MAMBA_ENV_NAME} && \
    #${MAMBA_EXE} install -y cctbx && \
    ${QCRBOX_PYTHON_VENV_DIR}/bin/python -m pip install --no-deps ${QCRBOX_HOME}/${QCRBOXTOOLS_WHEEL} && \
    true


ARG PYQCRBOX_PYTHON_PACKAGE_VERSION=${PYQCRBOX_PYTHON_PACKAGE_VERSION}
ARG PYQCRBOX_PYTHON_PACKAGE_WHEEL=pyqcrbox-${PYQCRBOX_PYTHON_PACKAGE_VERSION}-py3-none-any.whl
COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} ./pyqcrbox_dist/${PYQCRBOX_PYTHON_PACKAGE_WHEEL} ${QCRBOX_HOME}/
RUN ${QCRBOX_PYTHON_VENV_DIR}/bin/python -m pip install ${QCRBOX_HOME}/pyqcrbox-*.whl

RUN micromamba shell init --shell bash --root-prefix=${MAMBA_ROOT_PREFIX} && \
    echo "${MAMBA_EXE} activate ${QCRBOX_MAMBA_ENV_NAME}" >> ${QCRBOX_HOME}/.bashrc && \
    echo "alias conda=${MAMBA_EXE}" >> ${QCRBOX_HOME}/.bashrc

COPY --chown=${QCRBOX_USER}:${QCRBOX_GROUP} entrypoint.sh execute_startup_cmd.sh ./

ENTRYPOINT ["/opt/qcrbox/entrypoint.sh"]
