from qcrbox_wrapper import QCrBoxWrapper
from qcrbox_wrapper.qcrbox_wrapper import QCrBoxCommand, QCrBoxCommandBase, QCrBoxInteractiveCommand
from qcrboxtools.cif.cif2cif import can_run_command
from pathlib import Path
from typing import List
from hashlib import md5
import yaml

def get_yaml_locations():
    translation = {
        "Crystal Explorer": "CrystalExplorer",
        "Eval14/15": "Eval1X",
    }
    basedir = Path(__file__).parents[1] / 'services' / 'applications'
    yml_location_dict = {}
    yml_pathes = list(basedir.glob('*/*.yaml'))
    for yml_path in yml_pathes:
        with yml_path.open() as fobj:
            config = yaml.safe_load(fobj)
        app_name = translation.get(config['name'], config['name'])
        yml_location_dict[app_name] = yml_path

    return yml_location_dict

yml_location_dict = get_yaml_locations()

def get_mock_command(base_command: QCrBoxCommand) -> QCrBoxCommand:
    class MockCommand(type(base_command)):
        def can_run(self, input_cif_path) -> bool:
            return can_run_command(yml_location_dict[self.application_name], self.name, input_cif_path)
        
    if isinstance(base_command, QCrBoxCommand):
        return MockCommand(
            cmd_id=base_command.id,
            name=base_command.name,
            application_id=base_command.application_id,
            application_name=base_command.application_name,
            parameters=base_command.parameters,
            wrapper_parent=base_command.wrapper_parent
        )
    elif isinstance(base_command, QCrBoxInteractiveCommand):
        return MockCommand(
            cmd_id=base_command.id,
            name=base_command.name,
            application_id=base_command.application_id,
            application_name=base_command.application_name,
            parameters=base_command.parameters,
            gui_url = base_command.gui_url,
            wrapper_parent=base_command.wrapper_parent,
            run_cmd=base_command.run_cmd,
            prepare_cmd=base_command.prepare_cmd,
            finalise_cmd=base_command.finalise_cmd
        )
    else:
        raise NotImplementedError(f"Unknown command type: {type(base_command)}")


class MockWrapper(QCrBoxWrapper):
    @property
    def commands(self) -> List["QCrBoxCommandBase"]:
        original_commands = super().commands
        return [get_mock_command(cmd) for cmd in original_commands]