import os
import re
from pathlib import Path, PureWindowsPath

from qcrboxtools.cif.cif2cif import (
    cif_file_merge_to_unified_by_yml,
    cif_file_to_specific_by_yml,
)
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.robots.mopro import MoProImportRobot, MoProInpFile, MoProRobot
from qcrbox.util.wine import WinePathHelper

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_mopro.yaml"

lib_path = PureWindowsPath(os.environ["MOPRO_LIB_PATH"])
mopro_exe = PureWindowsPath(os.environ["MOPRO_PATH"])
import_mopro_exe = PureWindowsPath(os.environ["IMOPRO_PATH"])
mopro_roaming_dir = Path(os.environ["MOPRO_ROAMING_PROFILE_DIR"])


def clean_cif(cif_path, cleaned_cif_path):
    text = cif_path.read_text(encoding="utf-8", errors="replace")
    non_character_pattern = re.compile(
        r"[^\w\s\.,!?;:\'\"\-()\[\]{}<>|/\\@#%&*+=`~\^]"
    )
    cleaned_text = non_character_pattern.sub("?", text)
    cleaned_cif_path.write_text(cleaned_text, encoding="utf-8")


def table_path(table_type):
    match table_type:
        case "MoPro v24":
            table_name = lib_path / "mopro_v24.tab"
        #case "XD":
        #    table_name = lib_path / "mopro_xd.tab"
        case _:
            if not table_type.endswith(".tab"):
                table_type += ".tab"
            table_name = lib_path / table_type
    return table_name


def wave_function_path(wave_function_type):
    match wave_function_type:
        case "Su Coppens":
            wave_name = lib_path / "WAVEF_Su_Coppens_relativistic"
        case "Clementi Roetti":
            wave_name = lib_path / "WAVEF"
        #case "Mollynx":
        #    wave_name = lib_path / "WAVEF_Mollynx"
        case _:
            wave_name = lib_path / f"WAVEF_{wave_function_type}"
    return wave_name


def anom_path():
    return lib_path / "asf_Kissel.dat"


def density_path():
    return lib_path / "dens_sph_neu.tab"



def create_mopro_inis(work_dir, table_type, wavefunction_type):
    mopro_roaming_dir.mkdir(parents=True, exist_ok=True)

    wine_work_dir = PureWindowsPath("Y:\\")
    for part in Path(work_dir.absolute()).parts[4:]:
        wine_work_dir = wine_work_dir / part

    replace_dict = {
        "{{mopro_workdir}}": str(wine_work_dir),
        "{{tabl_path}}": str(table_path(table_type)),
        "{{wave_path}}": str(wave_function_path(wavefunction_type)),
        "{{anom_path}}": str(anom_path()),
        "{{dens_path}}": str(density_path()),
        "{{mopro_path}}": os.environ["MOPRO_PATH"],
        "{{vmopro_path}}": os.environ["VMOPRO_PATH"],
        "{{imopro_path}}": os.environ["IMOPRO_PATH"],
        "{{mopro_viewer_path}}": os.environ["MOPRO_VIEWER_PATH"],
    }

    for filename in Path("./templates").iterdir():
        with Path(filename).open("r", encoding="UTF-8") as fobj:
            content = fobj.read()
        for key, value in replace_dict.items():
            content = content.replace(key, value)
        with (mopro_roaming_dir / filename.name).open("w", encoding="UTF-8") as fobj:
            fobj.write(content)


def add_files_mopro_inp(inp_file: MoProInpFile, table_type: str, wave_function_type: str):
    inp_file.files["TABL"] = table_path(table_type)
    inp_file.files["WAVE"] = wave_function_path(wave_function_type)
    inp_file.files["ANOM"] = anom_path()
    return inp_file

def run_inp_file(
    input_cif_path,
    output_cif_path,
    inp_file_path,
    constraint_file_path,
    restraint_file_path,
    table_type,
    wavefunction_type
):
    work_folder = Path(input_cif_path).parent
    work_cif_path = work_folder / "work.cif"
    cif_file_to_specific_by_yml(
        input_cif_path, work_cif_path, YAML_PATH, "run_inp_file", "input_cif_path"
    )
    cif2hkl4(input_cif_path, 0, work_cif_path.with_suffix(".hkl"))

    mopro_ini_path = mopro_roaming_dir / "mopro.ini"
    if mopro_ini_path.exists():
        mopro_ini_path.unlink()

    path_helper = WinePathHelper()
    imopro_unix_path = path_helper.get_unix_path(Path(os.environ["IMOPRO_PATH"]))

    imopro = MoProImportRobot(executable_path=imopro_unix_path)
    imopro.cif2par(work_cif_path)

    path_helper = WinePathHelper()
    inp_file_path = Path(inp_file_path)
    inp_file = MoProInpFile.from_file(inp_file_path)
    add_files_mopro_inp(inp_file, table_type, wavefunction_type)
    para_path = work_cif_path.with_name(work_cif_path.stem + "_00.par")
    inp_file.files["PARA"] = path_helper.get_windows_path(para_path)
    inp_file.files["DATA"] = path_helper.get_windows_path(work_cif_path.with_suffix(".hkl"))
    if constraint_file_path.lower() != "none":
        inp_file.files["CONS"] = path_helper.get_windows_path(Path(constraint_file_path))
    else:
        inp_file.files.pop("CONS", None)
    if restraint_file_path.lower() != "none":
        inp_file.files["REST"] = path_helper.get_windows_path(Path(restraint_file_path))
    else:
        inp_file.files.pop("REST", None)
    inp_file.body += '\nWRIT CIFM\n'
    inp_file.write(work_folder / "mopro.inp")

    mopro_unix_path = path_helper.get_unix_path(Path(os.environ["MOPRO_PATH"]))
    mopro = MoProRobot(executable_path=mopro_unix_path)
    mopro.run_file(work_folder / "mopro.inp")

    excluded_cif = ("output.cif", "work.cif", "input.cif")
    newest_cif_path = next(
        reversed(
            sorted(
                (
                    file_path
                    for file_path in work_folder.glob("*.cif")
                    if file_path.name not in excluded_cif
                ),
                key=os.path.getmtime,
            )
        )
    )

    # MoPro might output invalid characters
    cleaned_cif_path = newest_cif_path.with_name("cleaned.cif")
    clean_cif(newest_cif_path, cleaned_cif_path)

    cif_file_merge_to_unified_by_yml(
        cleaned_cif_path,
        output_cif_path,
        input_cif_path,
        YAML_PATH,
        "run_inp_file",
        "output_cif_path",
    )


def prepare__interactive(input_cif_path, table_type, wavefunction_type):
    input_cif_path = Path(input_cif_path)
    work_dir = input_cif_path.parent
    work_cif_path = work_dir / "work.cif"
    cif_file_to_specific_by_yml(
        input_cif_path, work_cif_path, YAML_PATH, "interactive", "input_cif_path"
    )

    create_mopro_inis(work_dir, table_type, wavefunction_type)

    cif2hkl4(input_cif_path, 0, input_cif_path.with_suffix(".hkl"))

    path_helper = WinePathHelper()
    imopro_unix_path = path_helper.get_unix_path(Path(os.environ["IMOPRO_PATH"]))

    imopro = MoProImportRobot(executable_path=imopro_unix_path)
    imopro.cif2par(work_cif_path)


def finalise__interactive(input_cif_path, output_cif_path):
    output_cif_path = Path(output_cif_path)
    input_cif_path = Path(input_cif_path)
    work_folder = input_cif_path.parent
    try:
        excluded_cif = ("output.cif", "work.cif", "input.cif")
        newest_cif_path = next(
            reversed(
                sorted(
                    (
                        file_path
                        for file_path in work_folder.glob("*.cif")
                        if file_path.name not in excluded_cif
                    ),
                    key=os.path.getmtime,
                )
            )
        )

        # MoPro might output invalid characters
        cleaned_cif_path = newest_cif_path.with_name("cleaned.cif")
        clean_cif(newest_cif_path, cleaned_cif_path)

        cif_file_merge_to_unified_by_yml(
            cleaned_cif_path,
            output_cif_path,
            input_cif_path,
            YAML_PATH,
            "interactive",
            "output_cif_path",
        )
    except StopIteration:
        pass

def toparams__interactive(input_cif_path):
    input_cif_path = Path(input_cif_path)
    work_folder = input_cif_path.parent


def redo__interactive(input_cif_path):
    pass

if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
