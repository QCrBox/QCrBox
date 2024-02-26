ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY ./configure_qcrboxtools.py ./
COPY ./qcrbtls_replace_structure_glue.py ./
COPY ./qcrbtls_check_convergence_glue.py ./
COPY ./qcrbtls_iso2aniso_glue.py ./
COPY ./qcrbtls_to_unified_cif_glue.py ./
COPY ./config_qcrboxtools.yaml ./