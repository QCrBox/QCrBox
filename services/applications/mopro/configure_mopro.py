import os
import re
from pathlib import Path, PureWindowsPath

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.file_converter.hkl import cif2hkl4

from qcrbox.registry.client import ExternalCommand, QCrBoxRegistryClient

client = QCrBoxRegistryClient()
application = client.register_application(
    "MoProSuite",
    version="2022.07",
)
YAML_PATH = "./config_mopro.yaml"


def prepare__interactive(input_cif_path):
    input_cif_path = Path(input_cif_path)
    work_dir = input_cif_path.parent
    roaming_dir = Path("/opt/wine_installations/wine_win64/drive_c/users/qcrbox/AppData/Roaming/mopro")
    roaming_dir.mkdir(parents=True, exist_ok=True)
    work_cif = work_dir / "work.cif"
    cif_file_to_specific_by_yml(input_cif_path, work_cif, YAML_PATH, "interactive", "input_cif_path")

    wine_work_dir = PureWindowsPath("Y:\\")
    for part in Path(work_dir.absolute()).parts[4:]:
        wine_work_dir = wine_work_dir / part

    replace_dict = {"{{mopro_workdir}}": str(wine_work_dir)}
    for filename in Path("./templates").iterdir():
        with Path(filename).open("r", encoding="UTF-8") as fobj:
            content = fobj.read()
        for key, value in replace_dict.items():
            content = content.replace(key, value)
        with (roaming_dir / filename.name).open("w", encoding="UTF-8") as fobj:
            fobj.write(content)

    cif2hkl4(input_cif_path, 0, input_cif_path.with_suffix(".hkl"))

    # imopro_path = work_dir / "imopro.inp"
    # imopro_path.write_text(dedent(f"""\
    #         {wine_work_dir / "work.cif"}
    #         work_00.par
    #         I

    #         N

    #     """
    # ))
    # args =[
    #     "wine",
    #     "/opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/bin-win/Import2MoPro-2022-06.exe",
    #     "imopro.inp"
    # ]
    # process = subprocess.run(
    #     args,
    #     text=True,
    #     capture_output=True,
    #     check=False,
    #     cwd=work_dir
    # )

    # if process.returncode != 0:
    #     cmd = shlex.join(args)
    #     raise RuntimeError(
    #         f'Error when running command\n{cmd}\n'
    #         + f'\nSTDERR:\n{process.stderr}'
    #         + f'\n\nSTDOUT:\n{process.stdout}')


def finalise__interactive(input_cif_path, output_cif_path):
    output_cif_path = Path(output_cif_path)
    input_cif_path = Path(input_cif_path)
    work_folder = input_cif_path.parent
    try:
        excluded_cif = ("output.cif", "work.cif", "input.cif")
        newest_cif_path = next(
            reversed(
                sorted(
                    (file_path for file_path in work_folder.glob("*.cif") if file_path.name not in excluded_cif),
                    key=os.path.getmtime,
                )
            )
        )

        # MoPro might output invalid characters

        text = newest_cif_path.read_text(encoding="utf-8", errors="replace")
        non_character_pattern = re.compile(r"[^\w\s\.,!?;:\'\"\-()\[\]{}<>|/\\@#%&*+=`~]")
        cleaned_text = non_character_pattern.sub("?", text)
        cleaned_cif_path = newest_cif_path.with_name("cleaned.cif")
        cleaned_cif_path.write_text(cleaned_text, encoding="utf-8")

        cif_file_merge_to_unified_by_yml(
            cleaned_cif_path, output_cif_path, input_cif_path, YAML_PATH, "interactive", "output_cif_path"
        )
    except StopIteration:
        pass


cmd_interactive = ExternalCommand(
    "wine", "/opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/MoProGUI_Qt_win64/MoProGUI_win64.exe"
)

application.register_external_command(
    "interactive",
    cmd_interactive,
)

application.register_python_callable("prepare__interactive", prepare__interactive)

application.register_python_callable("finalise__interactive", finalise__interactive)

client.run()
