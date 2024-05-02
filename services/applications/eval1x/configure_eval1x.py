import json
import os
import pathlib
import shutil

from qcrboxtools.cif.merge import merge_cif_files
from qcrboxtools.robots.eval import (
    Eval15AllRobot,
    EvalAnyRobot,
    EvalBuilddatcolRobot,
    EvalPeakrefRobot,
    EvalViewRobot,
    PicFile,
    RmatFile,
    SettingsVicFile,
    TextFile,
)

from qcrbox.registry.client import ExternalCommand, FormattedParam, QCrBoxRegistryClient


def integrate(
    work_folder: str,
    rmat_file_path: str,
    beamstop_file_path: str,
    detalign_file_path: str,
    maximum_res: float,
    minimum_res: float,
    box_size: float,
    box_depth: int,
    maximum_duration: float,
    min_refln_in_box: int,
    pic_dir: str,
):
    work_folder = pathlib.Path(work_folder)
    rmat_file = pathlib.Path(rmat_file_path)
    if rmat_file.suffix == ".cif":
        new_rmat = RmatFile.from_cif_file("ic.rmat", rmat_file_path)
        new_rmat.to_file(work_folder)
        rmat_file_path = pathlib.Path(work_folder) / new_rmat.filename

    builddatcol(
        work_folder,
        rmat_file_path,
        beamstop_file_path,
        detalign_file_path,
        maximum_res,
        minimum_res,
        box_size,
        box_depth,
        maximum_duration,
        min_refln_in_box,
    )

    create_shoes(
        work_folder,
        rmat_file_path,
        beamstop_file_path,
        detalign_file_path,
        datcol_dir=work_folder,
    )

    eval15all(work_folder, pic_dir)

    create_reflection_cif(work_folder)

    final_cell_refinement(work_folder, rmat_file_path)

    merge_cif_files(
        work_folder / "intensities.cif",
        "0",
        work_folder / "cell.cif",
        "0",
        work_folder / "output.cif",
        "output",
    )


def builddatcol(
    work_folder: str,
    rmat_file_path: str,
    beamstop_file_path: str,
    detalign_file_path: str,
    maximum_res: float,
    minimum_res: float,
    box_size: float,
    box_depth: int,
    maximum_duration: float,
    min_refln_in_box: int,
):
    work_folder = pathlib.Path(work_folder)
    if rmat_file_path == "work_folder":
        rmat_file_path = next(reversed(sorted(work_folder.glob("*.rmat"), key=os.path.getmtime)))
    if beamstop_file_path != "work_folder":
        try:
            shutil.copy(beamstop_file_path, work_folder)
        except shutil.SameFileError:
            pass
    if detalign_file_path != "work_folder":
        try:
            shutil.copy(detalign_file_path, work_folder)
        except shutil.SameFileError:
            pass
    builddatcolrob = EvalBuilddatcolRobot(work_folder=work_folder)
    builddatcolrob.create_datcol_files(
        rmat_file=RmatFile.from_file(rmat_file_path),
        maximum_res=float(maximum_res),
        minimum_res=float(minimum_res),
        box_size=float(box_size),
        box_depth=int(box_depth),
        maximum_duration=float(maximum_duration),
        min_refln_in_box=int(min_refln_in_box),
    )


def create_shoes(
    work_folder: str,
    rmat_file_path: str,
    beamstop_file_path: str,
    detalign_file_path: str,
    datcol_dir: str,
):
    work_folder = pathlib.Path(work_folder)
    if rmat_file_path == "work_folder":
        rmat_file_path = next(reversed(sorted(work_folder.glob("*.rmat"), key=os.path.getmtime)))
    if beamstop_file_path == "work_folder":
        beamstop_file_path = next(reversed(sorted(work_folder.glob("beamstop.vic"), key=os.path.getmtime)))
    if detalign_file_path == "work_folder":
        detalign_file_path = next(reversed(sorted(work_folder.glob("detalign.vic"), key=os.path.getmtime)))
    if datcol_dir == "work_folder":
        datcol_dir = work_folder
    else:
        datcol_dir = pathlib.Path(datcol_dir)

    rmat_file = RmatFile.from_file(rmat_file_path)
    beamstop_file = SettingsVicFile.from_file(beamstop_file_path)
    detalign_file = SettingsVicFile.from_file(detalign_file_path)

    datcol_filepaths = sorted(datcol_dir.glob("datcol*.vic"))
    datcol_files = [TextFile.from_file(path) for path in datcol_filepaths]

    evalview = EvalViewRobot(
        work_folder=work_folder,
        file_list=[rmat_file, beamstop_file, detalign_file, *datcol_files],
    )

    evalview.create_shoes()


# def buildeval15(
#     work_folder,
#     focus_type,
#     polarisation_type,
#     pointspread_gamma,
#     acdnoise,
#     crystal_dimension,
#     mosaic
# ):
#     buildeval15rob = EvalBuildeval15Robot(work_folder=work_folder)
#     buildeval15rob.run(
#         focus_type,
#         polarisation_type,
#         pointspread_gamma,
#         acdnoise,
#         crystal_dimension,
#         mosaic
#     )


def eval15all(work_folder, pic_dir):
    work_folder = pathlib.Path(work_folder)
    if pic_dir == "work_folder":
        pic_dir = work_folder
    else:
        pic_dir = pathlib.Path(pic_dir)
    pic_files = [PicFile.from_file(path) for path in pic_dir.glob("*.pic")]

    if len(pic_files) == 0 and (pic_dir / "ic").exists():
        pic_files = [PicFile.from_file(path) for path in pic_dir.glob("ic/*.pic")]
    if len(list(work_folder.glob("*.sho*"))) == 0 and (work_folder / "ic").exists():
        work_folder = work_folder / "ic"

    eval15 = Eval15AllRobot(work_folder=work_folder, file_list=pic_files)

    eval15.integrate_shoes()


def create_reflection_cif(work_folder):
    work_folder = pathlib.Path(work_folder)

    if (work_folder / "ic").exists():
        anyrob = EvalAnyRobot(work_folder=work_folder / "ic")
    else:
        anyrob = EvalAnyRobot(work_folder=work_folder)

    anyrob.create_cif_file(work_folder / "intensities.cif")


def final_cell_refinement(work_folder, rmat_file_path):
    work_folder = pathlib.Path(work_folder)
    if rmat_file_path == "work_folder":
        rmat_file_path = next(reversed(sorted(work_folder.glob("*.rmat"), key=os.path.getmtime)))

    anyrob = EvalAnyRobot(work_folder=work_folder / "ic")
    anyrob.create_pk()

    peakref = EvalPeakrefRobot(work_folder=work_folder, rmat_file=RmatFile.from_file(rmat_file_path))

    peakref.refine_parameters("ic/final", new_rmat_filename="ic_refined.rmat", end_with_cell=True)

    peakref.folder_to_cif("cell.cif")


def finalise__interactive(work_folder, output_cif_path):
    work_folder = pathlib.Path(work_folder)
    create_reflection_cif(work_folder)
    final_cell_refinement(work_folder, "work_folder")

    merge_cif_files(
        work_folder / "intensities.cif",
        "0",
        work_folder / "cell.cif",
        "0",
        output_cif_path,
        "output",
    )


def toparams__interactive(work_folder, par_json, par_folder):
    work_folder = pathlib.Path(work_folder)
    par_folder = pathlib.Path(par_folder)
    # TODO Check if par_folder is empty?

    bdatcol = EvalBuilddatcolRobot(work_folder)
    tojson = bdatcol.extract_vars()

    output_cif_in = work_folder / "output.cif"
    output_cif_save = par_folder / "output.cif"
    if output_cif_in.exists():
        shutil.copy(output_cif_in, output_cif_save)
    else:
        rmat_file_path = next(reversed(sorted(work_folder.glob("*.rmat"), key=os.path.getmtime)))
        rmat = RmatFile.from_file(rmat_file_path)
        rmat.to_cif_file(output_cif_save, "output")

    tojson["rmat_file_path"] = "$par_folder/output.cif"

    beamstop_file_path = next(reversed(sorted(work_folder.glob("beamstop.vic"), key=os.path.getmtime)))

    shutil.copy(beamstop_file_path, par_folder / "beamstop.vic")

    tojson["beamstop_file_path"] = "$par_folder/beamstop.vic"

    detalign_file_path = next(reversed(sorted(work_folder.glob("detalign.vic"), key=os.path.getmtime)))

    shutil.copy(detalign_file_path, par_folder / "detalign.vic")

    tojson["detalign_file_path"] = "$par_folder/detalign.vic"

    pic_files_info = [(file.stat().st_mtime, file.parent) for file in work_folder.rglob("*.pic")]
    pic_folder_in = sorted(pic_files_info, key=lambda x: x[0], reverse=True)[0][1]
    pic_folder_out = par_folder / "pic_dir"
    pic_folder_out.mkdir(exist_ok=True)
    for file_path in pic_folder_in.glob("*.pic"):
        shutil.copy(file_path, pic_folder_out / file_path.name)

    tojson["pic_dir"] = "$par_folder/pic_dir"

    json_path = pathlib.Path(par_json)
    with json_path.open("w", encoding="UTF-8") as fobj:
        json.dump(tojson, fobj, indent=4)


def redo__interactive(work_folder, par_json, par_folder):
    with open(par_json, "r", encoding="UTF-8") as fobj:
        par_dict = json.load(fobj)
    for key in par_dict:
        if isinstance(par_dict[key], str):
            par_dict[key] = par_dict[key].replace("$par_folder", str(par_folder))
    integrate(work_folder=work_folder, **par_dict)


client = QCrBoxRegistryClient()
application = client.register_application("Eval1X", version="20230913")

application.register_external_command(
    "interactive",
    ExternalCommand(
        "lxterminal",
        FormattedParam("work_folder", format_string="--working-directory={}"),
    ),
)

application.register_python_callable("integrate", integrate)
application.register_python_callable("finalise__interactive", finalise__interactive)
application.register_python_callable("toparams__interactive", toparams__interactive)
application.register_python_callable("redo__interactive", redo__interactive)
client.run()
