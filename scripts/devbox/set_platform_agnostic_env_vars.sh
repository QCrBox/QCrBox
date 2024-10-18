# Ensure that 'uv pip install' uses the Python interpreter in the Devbox-managed virtual environnment.
export UV_PYTHON=$VENV_DIR/bin/python

# Ensure that hatch uses the uv binary and python interpreter installed via Devbox
export HATCH_ENV_TYPE_VIRTUAL_UV_PATH=$DEVBOX_PACKAGES_DIR/bin/uv
export HATCH_PYTHON=$DEVBOX_PACKAGES_DIR/bin/python
