import os
import shutil
import subprocess
from pathlib import Path

from pyqcrbox import logger, sql_models
from pyqcrbox.registry.client import QCrBoxClient
from qcrboxtools.cif.file_converter.tsc import TSCBFile

YAML_PATH = Path(__file__).parent / "config_olex2.yaml"

def generate_tscb_if_needed(input_cif):
    try:
        tscb_path = Path(input_cif).with_suffix(".tscb")
        tscb_obj = TSCBFile.from_cif_file(input_cif)
        tscb_obj.to_file(tscb_path)
        logger.info(f"Generated TSCB file at {tscb_path}")
        return tscb_path
    except ValueError as e:
        logger.info(f"XXX DEBUG MODE: Could not generate TSCB file from CIF with error:\n{str(e)}")
        return None

#def run__interactive(input_file):
#    logger.info("XXX DEBUG MODE: Running Olex2 via PythonCallable")
#    input_cif_path = Path(input_file)
#    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"
#    subprocess.run(
#        ["/bin/bash", "/opt/olex2/start", f"{work_cif_path}"],
#    )


def prepare__interactive(input_file):
    input_cif_path = Path(input_file)

    generate_tscb_if_needed(input_cif_path)

    # Remove files that might trigger Olex2 crash detection
    olex2_datadir = Path(os.getenv("OLEX2_DATADIR"))
    cache_file = olex2_datadir / "olx.cache"
    if cache_file.exists():
        cache_file.unlink()

    ready_files = olex2_datadir.glob("*.ready")
    for ready_file in ready_files:
        ready_file.unlink()

    pid_files = olex2_datadir.glob("*.olex2_pid")
    for pid_file in pid_files:
        pid_file.unlink()


def finalise__interactive(input_file, output_cif_name):
    input_file = Path(input_file)
    work_folder = input_file.parent

    newest_cif_path = max(
        ( file_path for file_path in work_folder.glob("*.cif")),
        key=os.path.getmtime,
    )

    output_cif_path = work_folder / output_cif_name
    shutil.copy(newest_cif_path, output_cif_path)

    return str(output_cif_path)


# def toparams__interactive(input_cif_path, parameter_json_path, parameter_folder):
#     input_cif_path = Path(input_cif_path)
#     work_folder = input_cif_path.parent
#     parameter_folder = Path(parameter_folder)

#     newest_cif_path = next(
#         reversed(
#             sorted(
#                 (file_path for file_path in work_folder.glob("*.cif") if file_path.name != "output.cif"),
#                 key=os.path.getmtime,
#             )
#         )
#     )

#     cif_file_merge_to_unified_by_yml(
#         newest_cif_path,
#         parameter_folder / "combine.cif",
#         input_cif_path,
#         YAML_PATH,
#         "interactive",
#         "output_cif_path",
#     )

#     tojson = {"structure_cif": "$par_folder/combine.cif"}
#     cif_text = (parameter_folder / "combine.cif").read_text().lower()
#     if "hirshfeld" in cif_text or "aspheric" in cif_text:
#         try:
#             newest_tsc_path = next(reversed(sorted(work_folder.glob("*.ts*"), key=os.path.getmtime)))
#             shutil.copy(
#                 newest_tsc_path,
#                 (parameter_folder / "work").with_suffix(newest_tsc_path.suffix),
#             )
#             tojson["tsc"] = "$par_folder/work" + newest_tsc_path.suffix
#         except StopIteration:
#             pass

#     json_path = Path(parameter_json_path)
#     with json_path.open("w", encoding="UTF-8") as fobj:
#         json.dump(tojson, fobj, indent=4)


# def redo__interactive(redo_input_cif_path, redo_output_cif_path, parameter_json_path, parameter_folder):
#     redo_input_cif_path = Path(redo_input_cif_path)
#     work_folder = redo_input_cif_path.parent
#     parameter_folder = Path(parameter_folder)
#     with open(parameter_json_path, encoding="UTF-8") as fobj:
#         par_dict = json.load(fobj)
#     for key in par_dict:
#         if isinstance(par_dict[key], str):
#             par_dict[key] = par_dict[key].replace("$par_folder", str(parameter_folder))

#     merge_cif = work_folder / "merge.cif"

#     replace_structure_from_cif(redo_input_cif_path, 0, par_dict["structure_cif"], 0, merge_cif)

#     work_cif = work_folder / "qcrbox_work.cif"

#     cif_file_to_specific_by_yml(merge_cif, work_cif, YAML_PATH, "interactive")

#     olex2_socket = Olex2Socket(structure_path=work_cif)
#     if "tsc" in par_dict:
#         tsc_path = Path(par_dict["tsc"])
#         new_tsc_path = (work_folder / "work").with_suffix(tsc_path.suffix)
#         shutil.copy(tsc_path, new_tsc_path)
#         olex2_socket.tsc_path = new_tsc_path

#     _ = olex2_socket.refine(n_cycles=10, refine_starts=5)

#     cif_file_merge_to_unified_by_yml(work_cif, redo_output_cif_path, redo_input_cif_path, YAML_PATH, "interactive")


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file("config_olex2.yaml")
    client = QCrBoxClient(application_spec=application_spec)
    client.run()
