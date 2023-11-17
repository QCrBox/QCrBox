FROM continuumio/miniconda3:23.3.1-0
SHELL ["/bin/bash", "--login", "-c"]

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        supervisor nano curl file wget rsync \
        gosu htop less ncdu procps psmisc tmux tree vim \
        tar cabextract gzip bzip2 zip unzip xzip xz-utils \
        gcc make bash-completion locales \
        openssh-client ca-certificates && \
    rm -rf /var/lib/apt/lists

# Install system-wide Python virtual environment and set up RabbitMQ RPC server
ARG QCRBOX_ROOT_DIR
ENV QCRBOX_ROOT_DIR=${QCRBOX_ROOT_DIR}
WORKDIR ${QCRBOX_ROOT_DIR}

ARG QCRBOX_PYTHON_VENV_DIR=${QCRBOX_ROOT_DIR}/venv
ARG QCRBOX_PYTHON_PACKAGE_VERSION=${QCRBOX_PYTHON_PACKAGE_VERSION}
RUN mkdir -p ${QCRBOX_PYTHON_VENV_DIR} && \
    python -m venv ${QCRBOX_PYTHON_VENV_DIR} && \
    ${QCRBOX_PYTHON_VENV_DIR}/bin/pip install -U pip wheel build

COPY ./qcrbox_dist/requirements.txt ${QCRBOX_ROOT_DIR}
#COPY  ./qcrbox_dist/requirements-dev.txt ${QCRBOX_ROOT_DIR}
RUN ${QCRBOX_PYTHON_VENV_DIR}/bin/pip install -r ${QCRBOX_ROOT_DIR}/requirements.txt && \
    #${QCRBOX_PYTHON_VENV_DIR}/bin/pip install -r ${QCRBOX_ROOT_DIR}/requirements-dev.txt && \
    true

COPY ./qcrbox_dist/qcrbox-${QCRBOX_PYTHON_PACKAGE_VERSION}-py3-none-any.whl ${QCRBOX_ROOT_DIR}/
RUN ${QCRBOX_PYTHON_VENV_DIR}/bin/pip install ${QCRBOX_ROOT_DIR}/qcrbox*.whl

ARG QCRBOX_SUPERVISORD_CONF_DIR=${QCRBOX_SUPERVISORD_CONF_DIR}
RUN mkdir -p ${QCRBOX_SUPERVISORD_CONF_DIR}/
# Create 'global' file /etc/supervisord.conf. This simply includes any config files
# present in QCRBOX_SUPERVISORD_CONF_DIR (which is where QCrBox services will put them).
RUN echo -e "[include]\nfiles = ${QCRBOX_SUPERVISORD_CONF_DIR}/*" > /etc/supervisord.conf
COPY supervisord.base_ancestor.conf ${QCRBOX_SUPERVISORD_CONF_DIR}/

ARG APP_USER=app
ARG APP_HOME=/home/app
ARG APP_USER_UID=1000
ARG APP_USER_GID=1000

RUN groupadd --gid ${APP_USER_GID} app && \
    useradd --home-dir ${APP_HOME} --shell /bin/bash --uid ${APP_USER_UID} --gid ${APP_USER_GID} ${APP_USER} && \
    mkdir -p ${APP_HOME}

ENV APP_USER=${APP_USER}
ENV APP_HOME=${APP_HOME}
WORKDIR ${APP_HOME}

ARG QCRBOX_HOST_RABBITMQ
ENV QCRBOX_HOST_RABBITMQ=${QCRBOX_HOST_RABBITMQ}

# By default, when logging into the container as root this activates the conda base environment.
# Let's disable this for the time being so that there is no interference with the QCrBox virtualenv.
RUN sed -i -e "s|. /opt/conda/etc/profile.d/conda.sh|#. /opt/conda/etc/profile.d/conda.sh|" /root/.bashrc
RUN sed -i -e "s|conda activate base|#conda activate base|" /root/.bashrc

# Add the QCrBox virtual environment to PATH so that the `qcb` command line tool is picked up.
#RUN echo 'export PATH=/opt/qcrbox/venv/bin/:$PATH' >> /etc/bash.bashrc

COPY entrypoint.sh ${QCRBOX_ROOT_DIR}
COPY bashrc_qcrbox.sh ${QCRBOX_ROOT_DIR}
#ENV BASH_ENV=${QCRBOX_ROOT_DIR}/bashrc_qcrbox.sh

# Add symlink to the `qcb` command line tool in `/usr/local/bin` so that it can get picked up in scripts
# without specifying the full path. (Unfortunately, amending PATH directly doesn't seem to be reliable.)
RUN ln -s ${QCRBOX_PYTHON_VENV_DIR}/bin/qcb /usr/local/bin/qcb

ENTRYPOINT ["/opt/qcrbox/entrypoint.sh"]
