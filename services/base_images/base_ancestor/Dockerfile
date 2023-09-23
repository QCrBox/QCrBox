FROM continuumio/miniconda3:23.3.1-0
SHELL ["/bin/bash", "-c"]

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        supervisor nano curl file wget rsync \
        gosu htop less ncdu procps psmisc tmux tree vim \
        tar cabextract gzip bzip2 zip unzip xzip xz-utils \
        gcc make bash-completion locales \
        openssh-client ca-certificates && \
    rm -rf /var/lib/apt/lists

# Install system-wide Python virtual environment and set up RabbitMQ RPC server
ARG QUBOX_ROOT_DIR
ENV QUBOX_ROOT_DIR=${QUBOX_ROOT_DIR}
WORKDIR ${QUBOX_ROOT_DIR}

ARG QUBOX_PYTHON_VENV_DIR=${QUBOX_ROOT_DIR}/venv
RUN mkdir -p ${QUBOX_PYTHON_VENV_DIR} && \
    python -m venv ${QUBOX_PYTHON_VENV_DIR} && \
    ${QUBOX_PYTHON_VENV_DIR}/bin/pip install -U pip wheel build

#COPY ./qubox_python_module ${QUBOX_ROOT_DIR}/qubox_python_module
#RUN ${QUBOX_PYTHON_VENV_DIR}/bin/pip install -e ${QUBOX_ROOT_DIR}/qubox_python_module/

ARG QUBOX_SUPERVISORD_CONF_DIR=${QUBOX_SUPERVISORD_CONF_DIR}
RUN mkdir -p ${QUBOX_SUPERVISORD_CONF_DIR}/
# Create 'global' file /etc/supervisord.conf. This simply includes any config files
# present in QUBOX_SUPERVISORD_CONF_DIR (which is where QuBox services will put them).
RUN echo -e "[include]\nfiles = ${QUBOX_SUPERVISORD_CONF_DIR}/*" > /etc/supervisord.conf
COPY supervisord.base_ancestor.conf ${QUBOX_SUPERVISORD_CONF_DIR}/

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

ARG QUBOX_HOST_RABBITMQ
ENV QUBOX_HOST_RABBITMQ=${QUBOX_HOST_RABBITMQ}

CMD ["sh", "-c", "chown -R --dereference -L ${APP_USER}:${APP_USER} ${APP_HOME} /tmp /dev/stdout && exec gosu ${APP_USER} supervisord"]
