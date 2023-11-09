ARG QCRBOX_DOCKER_TAG
FROM qcrbox/base-application:${QCRBOX_DOCKER_TAG}
SHELL ["/bin/bash", "-c"]

COPY ./shelx_executables/* /opt/shelx/bin/
COPY ./configure_shelx.py ./

ENV PATH="$PATH:/opt/shelx/bin/"

# CMD ["conda", "run", "-n", "xharpy_gpaw", "python", "-m", "xharpy.cli_tsc", "--cif_name", "/mnt/shared_files/xharpy_gpaw/input.cif", "--tsc_name", "/mnt/shared_files/xharpy_gpaw/output.tsc",  "--gridspacing", "0.24", "--auto_default"]
