import json
import os
import shutil
from pathlib import Path

from qcrboxtools.cif.merge import replace_structure_from_cif
from qcrboxtools.robots.olex2 import Olex2Socket

from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient


def finalise__interactive(
    work_folder
):
    work_folder = Path(work_folder)
    newest_cif_path = next(reversed(sorted(
        work_folder.glob('*.cif'), key=os.path.getmtime
    )))

    # TODO if not existing, rerun newest res with ACTA

    shutil.copy(newest_cif_path, work_folder / 'output.cif')


def toparams__interactive(
    work_folder,
    par_json,
    par_folder
):
    work_folder = Path(work_folder)
    par_folder = Path(par_folder)

    newest_cif_path = next(reversed(sorted(
        work_folder.glob('*.cif'), key=os.path.getmtime
    )))

    shutil.copy(newest_cif_path, par_folder / 'combine.cif')

    tojson = {'structure_cif': '$par_folder/combine.cif'}
    cif_text = (par_folder / 'combine.cif').read_text().lower()
    if 'hirshfeld' in cif_text or 'aspheric' in cif_text:
        try:
            newest_tsc_path = next(reversed(sorted(
                work_folder.glob('*.ts*'), key=os.path.getmtime
            )))
            shutil.copy(newest_tsc_path, (par_folder / 'work').with_suffix(newest_tsc_path.suffix))
            tojson['tsc'] = '$par_folder/work' + newest_tsc_path.suffix
        except StopIteration:
            pass

    json_path = Path(par_json)
    with json_path.open('w', encoding='UTF-8') as fobj:
        json.dump(tojson, fobj, indent=4)


def redo__interactive(
    input_cif,
    work_folder,
    par_json,
    par_folder
):
    work_folder = Path(work_folder)
    par_folder = Path(par_folder)
    with open(par_json, 'r', encoding='UTF-8') as fobj:
        par_dict = json.load(fobj)
    for key in par_dict:
        if isinstance(par_dict[key], str):
            par_dict[key] = par_dict[key].replace('$par_folder', str(par_folder))

    work_path = work_folder / 'work.cif'

    replace_structure_from_cif(
        input_cif,
        0,
        par_dict['structure_cif'],
        0,
        work_path
    )

    olex2_socket = Olex2Socket(structure_path=work_path)
    if 'tsc' in par_dict:
        tsc_path = Path(par_dict['tsc'])
        new_tsc_path = (work_folder / 'work').with_suffix(tsc_path.suffix)
        shutil.copy(tsc_path, new_tsc_path)
        olex2_socket.tsc_path = new_tsc_path

    _ = olex2_socket.refine(n_cycles=10, refine_starts=5)

    shutil.copy(work_path, work_folder / 'output.cif')



client = QCrBoxRegistryClient()
application = client.register_application("Olex2 (Linux)", version="1.5")
application.register_external_command(
    "interactive",
    ExternalCommand("/bin/bash", "/opt/olex2/start", Param("cif_path")),
)

external_cmd_refine_iam = ExternalCommand(
    "python", "/opt/qcrbox/olex2_glue_cli.py", "refine",
    "--structure_path", Param("cif_path"),
    "--n_cycles", Param("ls_cycles"),
    "--weight_cycles", Param("weight_cycles")
)

application.register_external_command("refine_iam", external_cmd_refine_iam)

external_cmd_refine_tsc = ExternalCommand(
    "python", "/opt/qcrbox/olex2_glue_cli.py", "refine",
    "--structure_path", Param("cif_path"),
    "--tsc_path", Param("tsc_path"),
    "--n_cycles", Param("ls_cycles"),
    "--weight_cycles", Param("weight_cycles")
)

application.register_external_command("refine_tsc", external_cmd_refine_tsc)

external_cmd_arbitry_cmds = ExternalCommand(
    "python", "/opt/qcrbox/olex2_glue_cli.py", "cmds",
    "--structure_path", Param("cif_path"),
    "--cmd_file_path", Param("cmd_file_path")
)

application.register_external_command("run_cmds_file", external_cmd_arbitry_cmds)
application.register_python_callable('finalise__interactive', finalise__interactive)
application.register_python_callable('toparams__interactive', toparams__interactive)
application.register_python_callable('redo__interactive', redo__interactive)
client.run()
