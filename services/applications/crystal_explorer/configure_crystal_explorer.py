
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_unified_yml_instr

from qcrbox.registry.client import ExternalCommand, Param, QCrBoxRegistryClient

YAML_PATH = "./config_crystal_explorer.yaml"

def prepare__interactive(input_cif_path):
    input_cif_path = Path(input_cif_path)
    work_folder = input_cif_path.parent
    work_cif = work_folder / "work.cif"

    cif_file_unified_yml_instr(input_cif_path, work_cif, YAML_PATH, "interactive")

cmd_open_file_in_crystal_explorer = ExternalCommand("/usr/bin/CrystalExplorer", "--open", Param("input_cif_path"))

client = QCrBoxRegistryClient()
application = client.register_application("CrystalExplorer", version="21.5")
application.register_external_command("interactive", cmd_open_file_in_crystal_explorer)
application.register_python_callable("prepare__interactive", prepare__interactive)
client.run()
