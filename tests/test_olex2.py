import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from qcrbox_wrapper import QCrBoxWrapper

from .common import with_temp_path_helper

load_dotenv(".env.dev")
FILEPATH = Path(__file__).parent / "test_files_olex"


# @pytest.mark.serial
@with_temp_path_helper
def test_refine_iam(tmp_path_helper):
    """
    Test whether the refinement command of the Olex2 container executes successfully (testing of
    the functionality of the underlying implementation is done in QCrBoxTools' tests)
    """
    shutil.copy(FILEPATH / "refine_nonconv_nonHaniso.cif", tmp_path_helper.path_to_local("input.cif"))

    qcrbox = QCrBoxWrapper(os.environ["QCRBOX_REGISTRY_HOST"], os.environ["QCRBOX_REGISTRY_PORT"])
    olex2 = qcrbox.application_dict["Olex2 (Linux)"]

    calc = olex2.refine_iam(
        input_cif_path=tmp_path_helper.path_to_qcrbox("input.cif"),
        ls_cycles="20",
        weight_cycles="5",
        output_cif_path=tmp_path_helper.path_to_qcrbox("output.cif"),
    )

    calc.wait_while_running(1.0)

    assert calc.status.status == "completed"
