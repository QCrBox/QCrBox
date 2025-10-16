import os
import re
import shutil
import subprocess
from pathlib import Path, PureWindowsPath

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient
from qcrboxtools.cif.cif2cif import cif_file_to_unified
from qcrboxtools.cif.file_converter.hkl import cif2hkl4
from qcrboxtools.robots.mopro import MoProImportRobot, MoProInpFile, MoProRobot
from qcrboxtools.util.wine import WinePathHelper

YAML_PATH = Path(__file__).parent / "config_mopro.yaml"

LIBMOPRO_PATH = PureWindowsPath(os.environ["MOPRO_LIB_PATH"])
MOPRO_EXE_PATH = PureWindowsPath(os.environ["MOPRO_PATH"])
IMPORT_MOPRO_EXE_PATH = PureWindowsPath(os.environ["IMOPRO_PATH"])
MOPRO_ROAMING_DIR = Path(os.environ["MOPRO_ROAMING_PROFILE_DIR"])


def __run_interactive(input_cif, output_cif_name):
    input_cif_path = Path(input_cif)
    work_dir = input_cif_path.parent

    path_helper = WinePathHelper()
    imopro_unix_path = path_helper.get_unix_path(Path(os.environ["IMOPRO_PATH"]))
    create_mopro_inis(work_dir, "MoPro v24", "Su Coppens")

    imopro = MoProImportRobot(executable_path=imopro_unix_path)
    imopro.cif2par(input_cif_path)

    # write hkl
    unified_cif_path = work_dir / "unified_for_hkl.cif"
    cif_file_to_unified(input_cif_path, unified_cif_path)
    cif2hkl4(unified_cif_path, 0, input_cif_path.with_suffix(".hkl"))
    unified_cif_path.unlink()

    mopro_gui_path = os.environ["MOPRO_GUI_PATH"]
    command = ["wine", str(mopro_gui_path)]

    subprocess.call(command)


def __finalise_interactive(input_cif, output_cif_name):
    input_cif_path = Path(input_cif)
    work_folder = input_cif_path.parent
    try:
        return write_output_cif(work_folder, output_cif_name)
    except FileNotFoundError:
        generate_cif_fcf(work_folder)
    return write_output_cif(work_folder, output_cif_name)


def generate_cif_fcf(work_folder):
    path_helper = WinePathHelper()
    newest_inp_file = find_newest_file_with_extension(work_folder, ".inp", case_sensitive=False)
    inp_file = MoProInpFile.from_file(newest_inp_file)
    newest_par_file = find_newest_file_with_extension(work_folder, ".par", case_sensitive=False)
    inp_file.files["PARA"] = path_helper.get_windows_path(newest_par_file)
    inp_file.body = "\nWRIT CIFM\nWRIT FCFW\n"
    inp_file.write(newest_inp_file.with_name("mopro_writecif.inp"))

    mopro_unix_path = path_helper.get_unix_path(Path(os.environ["MOPRO_PATH"]))
    mopro = MoProRobot(executable_path=mopro_unix_path)
    mopro.run_file(newest_inp_file.with_name("mopro_writecif.inp"))


def write_output_cif(work_folder, output_cif_name):
    output_cif_path = work_folder / output_cif_name
    try:
        newest_cif_path = find_newest_file_with_extension(
            work_folder, ".cif", files_to_exclude=["output.cif", "work.cif", "input.cif"], case_sensitive=False
        )
        newest_cif_text = newest_cif_path.read_text(encoding="utf-8", errors="replace")

        newest_fcf_path = find_newest_file_with_extension(work_folder, ".fcf", case_sensitive=False)
        newest_fcf_text = newest_fcf_path.read_text(encoding="utf-8", errors="replace")

        cif_text = newest_cif_text + "\n_iucr_refine_fcf_details\n;\n" + newest_fcf_text + "\n;\n"

        cleaned_text = clean_cif_text(cif_text)
        output_cif_path.write_text(cleaned_text, encoding="utf-8")

        return output_cif_path
    except StopIteration as e:
        raise FileNotFoundError("CIF or FCF files missing in the working directory.") from e


def clean_cif_text(cif_text):
    non_character_pattern = re.compile(r"[^\w\s\.,!?;:\'\"\-()\[\]{}<>|/\\@#%&*+=`~\^]")
    cleaned_text = non_character_pattern.sub("?", cif_text)

    # Replace invalid newline characters for specific entries (from fcf)
    replace_entries = (
        "_symmetry_space_group_name_Hall",
        "_symmetry_space_group_name_H-M_alt",
        "_space_group_IT_number",
    )
    for entry in replace_entries:
        pattern = re.compile(rf"(\n\s*{entry} .*\n)", re.IGNORECASE)
        match = pattern.search(cleaned_text)
        if match:
            value = match.group(1)
            cleaned_text = re.sub(pattern, value, cleaned_text)

    cleaned_text = re.sub(r"(\d+\.\d+\(\d+)\n", r"\1\)\n", cleaned_text)
    return cleaned_text


def find_newest_file_with_extension(work_folder, extension, files_to_exclude=None, case_sensitive=False):
    if files_to_exclude is None:
        files_to_exclude = []
    excluded_files_set = set(files_to_exclude)

    ending = extension[1:] if extension.startswith(".") else extension

    search = ending if case_sensitive else "".join(f"[{char.lower()}{char.upper()}]" for char in ending)

    matching_files = [
        file_path for file_path in work_folder.glob(f"*.{search}") if file_path.name not in excluded_files_set
    ]
    if not matching_files:
        raise FileNotFoundError(f"No files with extension {extension} found in {work_folder}")
    return max(matching_files, key=os.path.getmtime)


def table_path(table_type):
    match table_type:
        case "MoPro v24":
            table_name = LIBMOPRO_PATH / "mopro_v24.tab"
        # case "XD":
        #    table_name = lib_path / "mopro_xd.tab"
        case _:
            if not table_type.endswith(".tab"):
                table_type += ".tab"
            table_name = LIBMOPRO_PATH / table_type
    return table_name


def wave_function_path(wave_function_type):
    match wave_function_type:
        case "Su Coppens":
            wave_name = LIBMOPRO_PATH / "WAVEF_Su_Coppens_relativistic"
        case "Clementi Roetti":
            wave_name = LIBMOPRO_PATH / "WAVEF"
        # case "Mollynx":
        #    wave_name = lib_path / "WAVEF_Mollynx"
        case _:
            wave_name = LIBMOPRO_PATH / f"WAVEF_{wave_function_type}"
    return wave_name


def anom_path():
    return LIBMOPRO_PATH / "asf_Kissel.dat"


def density_path():
    return LIBMOPRO_PATH / "dens_sph_neu.tab"


def create_mopro_inis(work_dir, table_type, wavefunction_type):
    MOPRO_ROAMING_DIR.mkdir(parents=True, exist_ok=True)

    wine_work_dir = PureWindowsPath(r"Z:")
    for part in Path(work_dir.absolute()).parts:
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

    for filename in (Path(__file__).parent / "templates").iterdir():
        with Path(filename).open("r", encoding="UTF-8") as fobj:
            content = fobj.read()
        for key, value in replace_dict.items():
            content = content.replace(key, value)
        with (MOPRO_ROAMING_DIR / filename.name).open("w", encoding="UTF-8") as fobj:
            fobj.write(content)


def add_files_mopro_inp(inp_file: MoProInpFile, table_type: str, wave_function_type: str):
    inp_file.files["TABL"] = table_path(table_type)
    inp_file.files["WAVE"] = wave_function_path(wave_function_type)
    inp_file.files["ANOM"] = anom_path()
    return inp_file


def run_inp_file(
    input_cif,
    output_cif_name,
    inp_file,
    constraint_file,
    restraint_file,
    table_type,
    wavefunction_type,
):
    work_folder = Path(input_cif).parent
    work_cif_path = work_folder / "work.cif"
    shutil.copy2(input_cif, work_cif_path)
    cif2hkl4(input_cif, 0, work_cif_path.with_suffix(".hkl"))

    mopro_ini_path = MOPRO_ROAMING_DIR / "mopro.ini"
    if mopro_ini_path.exists():
        mopro_ini_path.unlink()

    path_helper = WinePathHelper()
    imopro_unix_path = path_helper.get_unix_path(Path(os.environ["IMOPRO_PATH"]))

    imopro = MoProImportRobot(executable_path=imopro_unix_path)
    imopro.cif2par(work_cif_path)

    path_helper = WinePathHelper()
    inp_file = Path(inp_file)
    inp_file = MoProInpFile.from_file(inp_file)
    add_files_mopro_inp(inp_file, table_type, wavefunction_type)
    para_path = work_cif_path.with_name(work_cif_path.stem + "_00.par")
    inp_file.files["PARA"] = path_helper.get_windows_path(para_path)
    inp_file.files["DATA"] = path_helper.get_windows_path(work_cif_path.with_suffix(".hkl"))
    inp_file.files["CONS"] = path_helper.get_windows_path(Path(constraint_file))
    inp_file.files["REST"] = path_helper.get_windows_path(Path(restraint_file))

    # inp_file.body += "\nWRIT CIFM\nWRIT FCFW\n"
    inp_file.write(work_folder / "mopro.inp")

    mopro_unix_path = path_helper.get_unix_path(Path(os.environ["MOPRO_PATH"]))
    mopro = MoProRobot(executable_path=mopro_unix_path)
    mopro.run_file(work_folder / "mopro.inp")

    try:
        return write_output_cif(work_folder, output_cif_name)
    except FileNotFoundError:
        generate_cif_fcf(work_folder)
    return write_output_cif(work_folder, output_cif_name)


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
