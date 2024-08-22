import json
from pathlib import Path

from qcrboxtools.cif.cif2cif import (
    cif_file_merge_to_unified_by_yml,
    cif_file_to_specific_by_yml,
)
from simple_cod_module import (
    cif_to_search_pars,
    download_cod_cif,
    get_fitting_cod_entries,
    get_number_fitting_cod_entries,
)
from pyqcrbox import sql_models_NEW_v2

from pyqcrbox.registry.client import QCrBoxClient

YAML_PATH = "./config_cod_check.yaml"


def parse_input(input_cif_path, cellpar_deviation_perc, listed_elements_only):
    # Convert string paths to Path objects for easier file handling
    input_cif_path = Path(input_cif_path)

    # Convert cellpar_deviation to the correct type and convert the given percentage to a decimal
    cellpar_deviation = float(cellpar_deviation_perc) / 100.0

    # Validate 'listed_elements_only' as a boolean value
    if listed_elements_only.lower() not in ("true", "false"):
        raise ValueError("'listed_elements_only' must be a boolean (true or false).")

    # Convert 'listed_elements_only' to a boolean
    listed_elements_only = listed_elements_only.lower() == "true"

    # Use the parent directory of the input CIF file as the working directory
    work_folder = input_cif_path.parent

    # Specify the path for the modified CIF file
    work_cif_path = work_folder / "qcrbox_work.cif"

    # Adjust the CIF file according to the requirements of 'simple_cod_module'
    cif_file_to_specific_by_yml(
        input_cif_path=input_cif_path,
        output_cif_path=work_cif_path,
        yml_path=YAML_PATH,  # Referencing the edited YAML configuration
        command="get_number_fitting_cod_entries",  # Command name as specified in the YAML
        parameter="input_cif_path",  # Parameter name as specified in the YAML
    )
    return work_cif_path, cellpar_deviation, listed_elements_only


def qcb_get_number_fitting_cod_entries(input_cif_path, cellpar_deviation_perc, listed_elements_only):
    # Transform input parameters from string to appropriate Python objects
    work_cif_path, cellpar_deviation, listed_elements_only = parse_input(
        input_cif_path, cellpar_deviation_perc, listed_elements_only
    )

    # Retrieve the number of matching entries
    elements, cell_dict = cif_to_search_pars(work_cif_path)
    n_entries = get_number_fitting_cod_entries(elements, cell_dict, cellpar_deviation, listed_elements_only)

    # Save the output as a JSON file
    with open(work_cif_path.parent / "nentries.json", "w", encoding="UTF-8") as fobj:
        json.dump({"n_entries": n_entries}, fobj)


def merge_closest_cod_entry(input_cif_path, output_cif_path, cellpar_deviation_perc, listed_elements_only):
    # cast the input parameters from strings to python objects
    work_cif_path, cellpar_deviation, listed_elements_only = parse_input(
        input_cif_path, cellpar_deviation_perc, listed_elements_only
    )

    output_cif_path = Path(output_cif_path)

    # get the list of fitting entries
    elements, cell_dict = cif_to_search_pars(work_cif_path)
    entry_lst = get_fitting_cod_entries(elements, cell_dict, cellpar_deviation, listed_elements_only)

    # if no fitting entries found, raise an error
    if len(entry_lst) == 0:
        raise ValueError("No fitting entries found")

    # download the cif file of the most fitting entry
    cod_cif_path = work_cif_path.parent / "cod.cif"
    download_cod_cif(entry_lst[0]["file"], cod_cif_path)

    # merge the input cif file with the downloaded cif file
    cif_file_merge_to_unified_by_yml(
        input_cif_path=cod_cif_path,
        output_cif_path=output_cif_path,
        merge_cif_path=input_cif_path,
        yml_path=YAML_PATH,
        command="merge_closest_cod_entry",
        parameter="output_cif_path",
    )


if __name__ == "__main__":
    application_spec = sql_models_NEW_v2.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
