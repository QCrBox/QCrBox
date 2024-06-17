from qcrbox.registry.client import ExternalCommand, QCrBoxRegistryClient
from pathlib import Path, PureWindowsPath
from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
import os

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

    replace_dict = {
        "{{mopro_workdir}}": str(wine_work_dir)
    }
    for filename in Path("./templates").iterdir():
        with Path(filename).open("r", encoding='UTF-8') as fobj:
            content = fobj.read()
        for key, value in replace_dict.items():
            content = content.replace(key, value)
        with (roaming_dir / filename.name).open("w", encoding='UTF-8') as fobj:
            fobj.write(content)


def finalise__interactive(input_cif_path, output_cif_path):
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
    cif_file_merge_to_unified_by_yml(newest_cif_path, output_cif_path, input_cif_path, YAML_PATH, "interactive", "output_cif_path")

cmd_interactive = ExternalCommand(
    "wine",
    "/opt/wine_installations/wine_win64/drive_c/MoProSuite-win-July2022/MoProGUI_Qt_win64/MoProGUI_win64.exe"
)





application.register_external_command(
    "interactive",
    cmd_interactive,
)

application.register_python_callable("prepare__interactive", prepare__interactive)

#application.register_python_callable("finalise__interactive", finalise__interactive)

client.run()
