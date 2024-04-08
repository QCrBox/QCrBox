import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from qcrbox_wrapper import QCrBoxWrapper

from .common import with_temp_path_helper

load_dotenv(".env.dev")
FILEPATH = Path(__file__).parent / "test_files_qcrboxtools"


@with_temp_path_helper
def test_check_convergence(tmp_path_helper):
    """
    Test whether the check_structure_convergence command of the QCrBoxTools container executes correctly
    As the overhead is low, the correct output is checked as well.
    """
    shutil.copy(FILEPATH / "difference_test1.cif", tmp_path_helper.path_to_local("input1.cif"))
    shutil.copy(FILEPATH / "difference_test2.cif", tmp_path_helper.path_to_local("input2.cif"))

    qcrbox = QCrBoxWrapper(os.environ["QCRBOX_REGISTRY_HOST"], os.environ["QCRBOX_REGISTRY_PORT"])
    qcrboxtools = qcrbox.application_dict["QCrBoxTools"]

    calc = qcrboxtools.check_structure_convergence(
        cif1_path=tmp_path_helper.path_to_qcrbox("input1.cif"),
        cif2_path=tmp_path_helper.path_to_qcrbox("input2.cif"),
        max_abs_position="0.001",
        max_position_su="1.0",
        max_abs_uij="0.005",
        max_uij_su="1.0",
        output_json=tmp_path_helper.path_to_qcrbox("output.json"),
    )

    calc.wait_while_running(0.2)

    assert calc.status.status == "completed"

    with open(tmp_path_helper.path_to_local("output.json"), encoding="UTF-8") as fobj:
        data = json.load(fobj)
        assert not data["converged"]

    calc2 = qcrboxtools.check_structure_convergence(
        cif1_path=tmp_path_helper.path_to_qcrbox("input1.cif"),
        cif2_path=tmp_path_helper.path_to_qcrbox("input1.cif"),
        max_abs_position="0.001",
        max_position_su="1.0",
        max_abs_uij="0.005",
        max_uij_su="1.0",
        output_json=tmp_path_helper.path_to_qcrbox("output2.json"),
    )

    calc2.wait_while_running(0.2)

    assert calc2.status.status == "completed"

    with open(tmp_path_helper.path_to_local("output2.json"), encoding="UTF-8") as fobj:
        data = json.load(fobj)
        assert data["converged"]
