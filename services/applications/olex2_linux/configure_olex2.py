import json
import os
import shutil
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.merge import replace_structure_from_cif
from qcrboxtools.robots.olex2 import Olex2Socket

from pyqcrbox import sql_models

#from pyqcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_olex2.yaml"


def prepare__interactive(input_cif_path, work_cif_path):
    input_cif_path = Path(input_cif_path)

    # create a cif file using the requested cif entries in olex2 format
    # will most likely be handled internally by QCrBox in the future
    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "interactive", "input_cif_path")


def finalise__interactive(input_cif_path, output_cif_path):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    work_folder = input_cif_path.parent

    newest_cif_path = next(
        reversed(
            sorted(
                (file_path for file_path in work_folder.glob("*.cif") if file_path.name != "output.cif"),
                key=os.path.getmtime,
            )
        )
    )

    # TODO if not existing, rerun newest res with ACTA

    # Go to unified keywords and split SUs into separate entries
    cif_file_merge_to_unified_by_yml(
        newest_cif_path, output_cif_path, input_cif_path, YAML_PATH, "interactive", "output_cif_path"
    )


def toparams__interactive(input_cif_path, parameter_json_path, parameter_folder):
    input_cif_path = Path(input_cif_path)
    work_folder = input_cif_path.parent
    parameter_folder = Path(parameter_folder)

    newest_cif_path = next(
        reversed(
            sorted(
                (file_path for file_path in work_folder.glob("*.cif") if file_path.name != "output.cif"),
                key=os.path.getmtime,
            )
        )
    )

    cif_file_merge_to_unified_by_yml(
        newest_cif_path, parameter_folder / "combine.cif", input_cif_path, YAML_PATH, "interactive", "output_cif_path"
    )

    tojson = {"structure_cif": "$par_folder/combine.cif"}
    cif_text = (parameter_folder / "combine.cif").read_text().lower()
    if "hirshfeld" in cif_text or "aspheric" in cif_text:
        try:
            newest_tsc_path = next(reversed(sorted(work_folder.glob("*.ts*"), key=os.path.getmtime)))
            shutil.copy(
                newest_tsc_path,
                (parameter_folder / "work").with_suffix(newest_tsc_path.suffix),
            )
            tojson["tsc"] = "$par_folder/work" + newest_tsc_path.suffix
        except StopIteration:
            pass

    json_path = Path(parameter_json_path)
    with json_path.open("w", encoding="UTF-8") as fobj:
        json.dump(tojson, fobj, indent=4)


def redo__interactive(redo_input_cif_path, redo_output_cif_path, parameter_json_path, parameter_folder):
    redo_input_cif_path = Path(redo_input_cif_path)
    work_folder = redo_input_cif_path.parent
    parameter_folder = Path(parameter_folder)
    with open(parameter_json_path, "r", encoding="UTF-8") as fobj:
        par_dict = json.load(fobj)
    for key in par_dict:
        if isinstance(par_dict[key], str):
            par_dict[key] = par_dict[key].replace("$par_folder", str(parameter_folder))

    merge_cif = work_folder / "merge.cif"

    replace_structure_from_cif(redo_input_cif_path, 0, par_dict["structure_cif"], 0, merge_cif)

    work_cif = work_folder / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(merge_cif, work_cif, YAML_PATH, "interactive")

    olex2_socket = Olex2Socket(structure_path=work_cif)
    if "tsc" in par_dict:
        tsc_path = Path(par_dict["tsc"])
        new_tsc_path = (work_folder / "work").with_suffix(tsc_path.suffix)
        shutil.copy(tsc_path, new_tsc_path)
        olex2_socket.tsc_path = new_tsc_path

    _ = olex2_socket.refine(n_cycles=10, refine_starts=5)

    cif_file_merge_to_unified_by_yml(work_cif, redo_output_cif_path, redo_input_cif_path, YAML_PATH, "interactive")


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file("config_olex2.yaml")

    client = QCrBoxClient(application_spec=application_spec)
    #application = client.register_application("Olex2 (Linux)", version="1.5")
    # application.register_external_command(
    #     "interactive",
    #     ExternalCommand("/bin/bash", "/opt/olex2/start", Param("input_cif_path")),
    # )

    # application.register_python_callable("prepare__interactive", prepare__interactive)
    # application.register_python_callable("finalise__interactive", finalise__interactive)
    # application.register_python_callable("toparams__interactive", toparams__interactive)
    # application.register_python_callable("redo__interactive", redo__interactive)
    client.run()
