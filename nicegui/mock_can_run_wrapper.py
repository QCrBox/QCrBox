from qcrbox_wrapper import QCrBoxWrapper
from qcrbox_wrapper.qcrbox_wrapper import QCrBoxCommand, QCrBoxCommandBase, QCrBoxInteractiveCommand
from pathlib import Path
from typing import List
from hashlib import md5

can_run_lookup = {
    ('COD Check', 'get_number_fitting_cod_entries', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('COD Check', 'merge_closest_cod_entry', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('CrysalisPro', 'interactive', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('CrystalExplorer', 'interactive', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('Eval1X', 'interactive', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('Eval1X', 'integrate', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('Olex2 (Linux)', 'interactive', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('Olex2 (Linux)', 'refine_iam', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('Olex2 (Linux)', 'refine_tsc', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('Olex2 (Linux)', 'run_cmds_file', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('QCrBoxTools', 'replace_structure_from_cif', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('QCrBoxTools', 'check_structure_convergence', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('QCrBoxTools', 'iso2aniso', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('QCrBoxTools', 'to_unified_cif', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): True,
    ('XHARPy-GPAW', 'atom_form_fact_gpaw', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('XHARPy-GPAW', 'ha_refine', '9dff3be99f4bb4f5fcdbc1d3cf1a6ff6'): False,
    ('COD Check', 'get_number_fitting_cod_entries', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('COD Check', 'merge_closest_cod_entry', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('CrysalisPro', 'interactive', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('CrystalExplorer', 'interactive', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Eval1X', 'interactive', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Eval1X', 'integrate', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Olex2 (Linux)', 'interactive', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Olex2 (Linux)', 'refine_iam', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Olex2 (Linux)', 'refine_tsc', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('Olex2 (Linux)', 'run_cmds_file', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('QCrBoxTools', 'replace_structure_from_cif', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('QCrBoxTools', 'check_structure_convergence', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('QCrBoxTools', 'iso2aniso', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('QCrBoxTools', 'to_unified_cif', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('XHARPy-GPAW', 'atom_form_fact_gpaw', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('XHARPy-GPAW', 'ha_refine', 'a40b800ab4e8e7d7a91cc5bb0cbc819c'): True,
    ('COD Check', 'get_number_fitting_cod_entries', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('COD Check', 'merge_closest_cod_entry', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('CrysalisPro', 'interactive', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('CrystalExplorer', 'interactive', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Eval1X', 'interactive', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Eval1X', 'integrate', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Olex2 (Linux)', 'interactive', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Olex2 (Linux)', 'refine_iam', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Olex2 (Linux)', 'refine_tsc', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('Olex2 (Linux)', 'run_cmds_file', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('QCrBoxTools', 'replace_structure_from_cif', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('QCrBoxTools', 'check_structure_convergence', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('QCrBoxTools', 'iso2aniso', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('QCrBoxTools', 'to_unified_cif', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('XHARPy-GPAW', 'atom_form_fact_gpaw', '207eaecc00fdbf2d034f8ff101f3b86a'): True,
    ('XHARPy-GPAW', 'ha_refine', '207eaecc00fdbf2d034f8ff101f3b86a'): False
}

def get_mock_command(base_command: QCrBoxCommand) -> QCrBoxCommand:
    class MockCommand(type(base_command)):
        def can_run(self, input_cif_path) -> bool:
            cif_hash = md5(Path(input_cif_path).read_bytes()).hexdigest()
            return can_run_lookup[(self.application_name, self.name, cif_hash)]

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