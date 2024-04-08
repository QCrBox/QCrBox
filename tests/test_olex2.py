import os
import shutil
from pathlib import Path

import pytest
from dotenv import load_dotenv

from qcrbox_wrapper import QCrBoxWrapper

from .common import with_temp_path_helper

load_dotenv(".env.dev")
FILEPATH = Path(__file__).parent / "test_files_olex"


@pytest.mark.serial
@with_temp_path_helper
def test_refine_iam(tmp_path_helper):
    shutil.copy(FILEPATH / "refine_nonconv_nonHaniso.cif", tmp_path_helper.path_to_local("input.cif"))

    qcrbox = QCrBoxWrapper(os.environ["QCRBOX_REGISTRY_HOST"], os.environ["QCRBOX_REGISTRY_PORT"])
    olex2 = qcrbox.application_dict["Olex2 (Linux)"]

    calc = olex2.refine_iam(
        input_cif_path=tmp_path_helper.path_to_qcrbox("input.cif"), ls_cycles="20", weight_cycles="5"
    )

    calc.wait_while_running(1.0)

    assert calc.status.status == "completed"


@pytest.mark.serial
@with_temp_path_helper
def test_refine_tsc(tmp_path_helper):
    shutil.copy(FILEPATH / "refine_nonconv_nonHaniso.cif", tmp_path_helper.path_to_local("input.cif"))
    shutil.copy(FILEPATH / "refine_allaniso.tscb", tmp_path_helper.path_to_local("input.tscb"))

    qcrbox = QCrBoxWrapper(os.environ["QCRBOX_REGISTRY_HOST"], os.environ["QCRBOX_REGISTRY_PORT"])
    olex2 = qcrbox.application_dict["Olex2 (Linux)"]

    calc = olex2.refine_tsc(
        input_cif_path=tmp_path_helper.path_to_qcrbox("input.cif"),
        tsc_path=tmp_path_helper.path_to_qcrbox("input.tscb"),
        ls_cycles="20",
        weight_cycles="5",
    )

    calc.wait_while_running(1.0)

    assert calc.status.status == "completed"
