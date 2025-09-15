import hashlib
from pathlib import Path
from typing import Optional

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.robots.olex2 import Olex2Socket

YAML_PATH = "/opt/qcrbox/config_olex2.yaml"


def refine(command_name: str, input_cif_path: str, output_cif_path: str, ls_cycles: int, weight_cycles: int, tsc_path: Optional[str] = None):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    tsc_path = Path(tsc_path) if tsc_path else None

    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, command_name, "input_cif_path")

    olex2_socket = Olex2Socket(structure_path=work_cif_path)

    if tsc_path:
        olex2_socket.tsc_path = tsc_path

    _ = olex2_socket.refine(n_cycles=ls_cycles, refine_starts=weight_cycles)

    cif_file_merge_to_unified_by_yml(
        work_cif_path, 0, output_cif_path, input_cif_path, YAML_PATH, command_name, "output_cif_path"
    )

def refine_iam(input_cif_path: str, output_cif_path: str, ls_cycles: str, weight_cycles: str):
    refine("Refine IAM", input_cif_path, output_cif_path, int(ls_cycles), int(weight_cycles))
    return str(output_cif_path)

def refine_tsc(input_cif_path: str, output_cif_path: str, tsc_path: str, ls_cycles: str, weight_cycles: str):
    refine("Refine with TSC(B)", input_cif_path, output_cif_path, int(ls_cycles), int(weight_cycles), tsc_path)
    return str(output_cif_path)

def run_commands(input_cif_path: str, output_cif_path: str, cmd_file_path: str, tsc_path: Optional[str] = None):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "run_cmds_file", "input_cif_path")

    olex2_socket = Olex2Socket(structure_path=work_cif_path)

    hash0 = hashlib.md5(work_cif_path.read_bytes()).hexdigest()

    if tsc_path:
        olex2_socket.tsc_path = tsc_path

    cmd_string = cmd_file_path.read_text(encoding="UTF-8")

    olex2_socket.send_command(cmd_string)

    hash1 = hashlib.md5(work_cif_path.read_bytes()).hexdigest()

    if hash0 != hash1 and output_cif_path is not None:
        cif_file_merge_to_unified_by_yml(
            work_cif_path, output_cif_path, input_cif_path, YAML_PATH, "run_cmds_file", "output_cif_path"
        )
        return str(output_cif_path)
    else:
        return None
    
def run_cmds_file_iam(input_cif_path: Path, output_cif_path: Path, cmd_file_path: Path):
    result = run_commands(input_cif_path, output_cif_path, cmd_file_path, None)
    if result is not None:
        return str(result)

def run_cmds_file_tsc(input_cif_path: Path, output_cif_path: Path, cmd_file_path: Path, tsc_path: Path):
    result = run_commands(input_cif_path, output_cif_path, cmd_file_path, tsc_path)
    if result is not None:
        return str(result)