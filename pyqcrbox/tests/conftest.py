import sys
from pathlib import Path

import pytest

from pyqcrbox import sql_models

#
# Insert the QCrBox repository root at the beginning of `sys.path`.
# This ensures that `import pyqcrbox` will always import the local
# version of `pyqcrbox` (even if it is already installed in the
# current virtual environment) and that the tests are run against
# this local version.
#
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_db_url(tmp_path):
    return f"sqlite:///{tmp_path}/test_registry_db.sqlite"


@pytest.fixture
def sample_application_spec():
    return sql_models.ApplicationCreate(
        name="Olex2",
        slug="olex2_linux",
        version="x.y.z",
        description=None,
        url="https://www.olexsys.org/olex2/",
        email="helpdesk@olexsys.org",
        commands=[
            sql_models.CommandCreate(
                name="refine_iam",
                implemented_as=sql_models.command.ImplementedAs("CLI"),
                parameters=[
                    sql_models.ParameterCreate(name="cif_file", type="str"),
                    sql_models.ParameterCreate(name="ls_cycles", type="int", required=False, default_value=5),
                    sql_models.ParameterCreate(name="weight_cycles", type="int", required=False, default_value=5),
                ],
            )
        ],
    )
