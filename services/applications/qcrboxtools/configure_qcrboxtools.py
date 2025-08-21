import json
from pathlib import Path

from qcrboxtools.analyse.convergence import check_converged
from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml, cif_file_to_unified
from qcrboxtools.cif.iso2aniso import cif_iso2aniso

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_qcrboxtools.yaml"


def check_structure_convergence(cif1, cif2, output_json_path, convergence_criterion, criterion_value):
    # Convert paths in Path objects and CIFs into unified format
    cif1 = Path(cif1)
    cif2 = Path(cif2)
    converted1_path = cif1.parent / "converted1.cif"
    converted2_path = cif2.parent / "converted2.cif"
    cif_file_to_specific_by_yml(cif1, converted1_path, YAML_PATH, "check_structure_convergence", "cif1")
    cif_file_to_specific_by_yml(cif2, converted2_path, YAML_PATH, "check_structure_convergence", "cif2")

    # This is the criteria we want
    mean_abs_position = None
    mean_position_su = None
    mean_abs_uij = None
    mean_uij_su = None

    # these should be parameters for the command
    max_abs_position = None
    max_position_su = None
    max_abs_uij = None
    max_uij_su = None

    criteria = {
        "max abs position": max_abs_position,
        "mean abs position": mean_abs_position,
        "max position/su": max_position_su,
        "mean position/su": mean_position_su,
        "max abs uij": max_abs_uij,
        "mean abs uij": mean_abs_uij,
        "max uij/su": max_uij_su,
        "mean uij/su": mean_uij_su,
    }

    # Insert the desired value in the desired criteria
    criteria[convergence_criterion.replace("_", " ")] = criterion_value

    # Remove criteria set to None
    criteria = {k: v for k, v in criteria.items() if v is not None}

    cif1_dataset = 0
    cif2_dataset = 0

    is_converged = check_converged(converted1_path, cif1_dataset, converted2_path, cif2_dataset, criteria)

    # clean up the converted structure
    converted1_path.unlink()
    converted2_path.unlink()

    result = {"converged": is_converged}
    output_json_path = Path(output_json_path)
    with output_json_path.open("w") as f:
        json.dump(result, f)

    print(f"Convergence check: {'Converged' if is_converged else 'Not converged'}")

    return str(output_json_path)


def to_unified_cif(input_cif, output_cif_name):
    output_cif_path = Path(input_cif).parent / output_cif_name
    cif_file_to_unified(
        input_cif_path=input_cif,
        output_cif_path=output_cif_path,
        convert_keywords=True,
        custom_categories=None,
        split_sus=True,
    )

    return str(output_cif_path)


def replace_structure_from_cif(input_cif, structure_cif, output_cif_name):
    from qcrboxtools.cif.merge import replace_structure_from_cif

    cif_dataset = "0"
    structure_cif_path = Path(structure_cif)
    work_cif_path = input_cif.parent / "qcrbox_work.cif"
    work_structure_cif_path = structure_cif_path.parent / "qcrbox_structure.cif"

    cif_file_to_specific_by_yml(input_cif, work_cif_path, YAML_PATH, "replace_structure_from_cif", "input_cif")

    cif_file_to_specific_by_yml(
        structure_cif_path, work_structure_cif_path, YAML_PATH, "replace_structure_from_cif", "structure_cif"
    )

    replaced_cif_path = input_cif.parent / "qcrbox_replaced.cif"

    replace_structure_from_cif(work_cif_path, cif_dataset, work_structure_cif_path, structure_cif, replaced_cif_path)

    output_cif_path = Path(input_cif).parent / output_cif_name
    cif_file_merge_to_unified_by_yml(
        replaced_cif_path, output_cif_path, input_cif, YAML_PATH, "replace_structure_from_cif", "output_cif_name"
    )

    return str(output_cif_path)


def iso2aniso(input_cif, output_cif_name):
    input_cif_path = Path(input_cif)
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "iso2aniso", "input_cif_name")

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
