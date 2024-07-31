from pathlib import Path

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml

from pyqcrbox import sql_models_NEW_v2
from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_{{ cookiecutter.application_slug }}.yaml"

def needed_as_function_name_not_sample_cmd_v2(
        input_cif_path: Path,
        output_cif_path: Path,
        msg: str,
        some_number: int
    ):
    input_cif_path = Path(input_cif_path)
    output_cif_path = Path(output_cif_path)
    work_cif_path = input_cif_path.with_name("qcrbox_work.cif")

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YAML_PATH, "sample_cmd_v2", "input_cif_path")

    # Do something with the cif file here

    cif_file_merge_to_unified_by_yml(
        work_cif_path, output_cif_path,
        input_cif_path, YAML_PATH,
        "sample_cmd_v2",
        "output_cif_path"
    )


if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file(
        "config_{{ cookiecutter.application_slug }}.yaml"
    )

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
