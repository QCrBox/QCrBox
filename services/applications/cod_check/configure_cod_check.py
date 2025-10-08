from pathlib import Path

from pyqcrbox import sql_models
from pyqcrbox.registry.client import QCrBoxClient
from simple_cod_module import (
    cif_to_search_pars,
    download_cod_cif,
    get_fitting_cod_entries,
)

YAML_PATH = Path(__file__).parent / "config_cod_check.yaml"


def merge_closest_cod_entry(input_cif, output_cif_name, cellpar_deviation_perc, listed_elements_only):
    cellpar_deviation = float(cellpar_deviation_perc) / 100.0

    input_cif = Path(input_cif)
    output_cif_path = input_cif.parent / output_cif_name

    # get the list of fitting entries
    elements, cell_dict = cif_to_search_pars(input_cif)
    entry_lst = get_fitting_cod_entries(elements, cell_dict, cellpar_deviation, listed_elements_only)

    # if no fitting entries found, raise an error
    if len(entry_lst) == 0:
        raise ValueError("No fitting entries found")

    # download the cif file of the most fitting entry
    # cod_cif_path = input_cif.parent / "cod.cif"
    download_cod_cif(entry_lst[0]["file"], output_cif_path)

    return str(output_cif_path)


if __name__ == "__main__":
    application_spec = sql_models.ApplicationSpec.from_yaml_file(YAML_PATH)

    client = QCrBoxClient(application_spec=application_spec)
    client.run()
