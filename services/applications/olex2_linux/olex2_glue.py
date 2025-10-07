from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.robots.olex2 import Olex2Socket
from qcrboxtools.cif.file_converter.tsc import TSCBFile

YAML_PATH = "/opt/qcrbox/config_olex2.yaml"

def generate_tscb_if_needed(input_cif):
    try:
        tscb_path = Path(input_cif).with_suffix(".tscb")
        tscb_obj = TSCBFile.from_cif_file(input_cif)
        tscb_obj.to_file(tscb_path)
        return tscb_path
    except ValueError:
        return None

def refine(
    input_cif_path: str,
    output_cif_path: str,
    ls_cycles: int,
    weight_cycles: int,
):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    tsc_path = generate_tscb_if_needed(input_cif_path)

    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "Refine", "input_cif_path")

    olex2_socket = Olex2Socket()

    _ = olex2_socket.run_full_refinement(work_cif_path, tsc_path, n_cycles=ls_cycles, refine_starts=weight_cycles)

    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path, input_cif_path, YAML_PATH, "Refine", "output_cif_path"
    )

    return str(output_cif_path)


def run_commands(input_cif_path: str, output_cif_path: str, cmd_file_path: str):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "run_cmds_file", "input_cif_path")

    olex2_socket = Olex2Socket()

    tsc_path = generate_tscb_if_needed(input_cif_path)

    cmd_string = Path(cmd_file_path).read_text(encoding="UTF-8")

    olex2_socket.send_command(work_cif_path, tsc_path, cmd_string)

    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path, input_cif_path, YAML_PATH, "run_cmds_file", "output_cif_path"
    )
    return str(output_cif_path)
