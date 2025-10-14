import shutil
from pathlib import Path

from qcrboxtools.cif.file_converter.tsc import TSCBFile
from qcrboxtools.robots.olex2 import Olex2Socket

YAML_PATH = Path(__file__).parent / "config_olex2.yaml"


def generate_tscb_if_needed(input_cif):
    try:
        tscb_path = Path(input_cif).with_suffix(".tscb")
        tscb_obj = TSCBFile.from_cif_file(input_cif)
        tscb_obj.to_file(tscb_path)
        return tscb_path
    except ValueError:
        return None


def refine(
    input_cif: str,
    output_cif_name: str,
    ls_cycles: int,
    weight_cycles: int,
):
    input_cif_path = Path(input_cif)
    output_cif_path = input_cif_path.parent / output_cif_name
    tsc_path = generate_tscb_if_needed(input_cif_path)

    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    shutil.copy(input_cif_path, work_cif_path)
    olex2_socket = Olex2Socket()

    _ = olex2_socket.run_full_refinement(work_cif_path, tsc_path, n_cycles=ls_cycles, refine_starts=weight_cycles)

    shutil.copy(work_cif_path, output_cif_path)

    return str(output_cif_path)


def run_commands(input_cif: str, output_cif_name: str, cmd_file: str):
    input_cif_path = Path(input_cif)
    output_cif_path = Path(output_cif_name)
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    shutil.copy(input_cif_path, work_cif_path)
    olex2_socket = Olex2Socket()

    tsc_path = generate_tscb_if_needed(input_cif_path)

    cmd_string = Path(cmd_file).read_text(encoding="UTF-8")

    olex2_socket.send_command(work_cif_path, tsc_path, cmd_string)

    shutil.copy(work_cif_path, output_cif_path)

    return str(output_cif_path)
