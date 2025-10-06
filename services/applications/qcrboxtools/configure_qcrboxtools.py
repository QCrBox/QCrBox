import json
from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml, cif_file_to_unified
from qcrboxtools.cif.iso2aniso import cif_iso2aniso

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_qcrboxtools.yaml"




def replace_structure_from_cif(input_cif, structure_cif, output_cif_name):
    from qcrboxtools.cif.merge import replace_structure_from_cif

    cif_dataset = 0
    input_cif = Path(input_cif)
    structure_cif_path = Path(structure_cif)
    work_cif_path = input_cif.parent / "qcrbox_work.cif"
    work_structure_cif_path = structure_cif_path.parent / "qcrbox_structure.cif"

    cif_file_to_specific_by_yml(input_cif, work_cif_path, YAML_PATH, "replace_structure_from_cif", "input_cif")

    cif_file_to_unified(
        input_cif_path=structure_cif_path,
        output_cif_path=work_structure_cif_path,
        convert_keywords=True,
        custom_categories=['iucr, olex2, shelx'],
        split_sus=True,
    )

    replaced_cif_path = input_cif.parent / "qcrbox_replaced.cif"

    replace_structure_from_cif(
        work_cif_path,
        cif_dataset,
        work_structure_cif_path,
        0, 
        replaced_cif_path,
    )

    output_cif_path = Path(input_cif).parent / output_cif_name
    cif_file_merge_to_unified_by_yml(
        replaced_cif_path, output_cif_path, input_cif, YAML_PATH, "replace_structure_from_cif", "output_cif_name"
    )

    return str(output_cif_path)


def iso2aniso(input_cif, output_cif_name):
    input_cif_path = Path(input_cif)
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "iso2aniso", "input_cif")

    # There were the original default values set via command line parameters when they were optional arguments/options
    select_names = None
    select_elements = None
    select_regexes = None
    overwrite = False

    # Call the function with parsed arguments
    cif_iso2aniso(
        input_cif_path=work_cif_path,
        cif_dataset="0",
        output_cif_path=work_cif_path,
        select_names=select_names,
        select_elements=select_elements,
        select_regexes=select_regexes,
        overwrite=overwrite,
    )

    output_cif_path = input_cif_path.parent / output_cif_name
    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path, input_cif_path, YAML_PATH, "iso2aniso", "output_cif_name"
    )

    return output_cif_path


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
