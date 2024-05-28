"""
Crystallographic Open Database Helper Module
============================================

This module provides a collection of functions designed to seach for crystallographic
data within the Crystallography Open Database (COD). It includes utilities for parsing
Crystallographic Information File (CIF) data, extracting essential parameters such
as chemical elements and unit cell parameters, and preparing data for database queries.
Be nice using this functionality. If you want to download large amounts of data, check
the COD website for better tools to achieve this goal. Do not be the reason that
restrictions have to be placed onto these APIs in the future, slowing down the research
of everyone.

Features:
---------
- Extraction of chemical elements and cell parameters from CIF files for database
  search criteria.
- Utilities for counting and retrieving matching database entries based on the
  extracted cell parameters and elements.
- Calculation of cell difference scores to assist in sorting and analyzing search
  results based on their geometric similarity to the cell parameters.
- Download of an entry via COD id.

Dependencies:
-------------
- qcrboxtools: A third-party library used for safe reading and processing of CIF files.
- requests: Required for making HTTP requests to the COD or similar databases for
  retrieving or counting matching entries.
"""

from pathlib import Path
from typing import Dict, List, Tuple

import requests
from qcrboxtools.cif.read import cifdata_str_or_index, read_cif_safe

COD_REST_URL = "https://www.crystallography.net/cod/result"


def cif_to_search_pars(input_cif_path: Path) -> Tuple[List[str], Dict[str, float]]:
    """
    Extracts elements and cell parameters from a CIF file for search purposes.

    This function extracts the chemical formula to identify elements and gathers cell
    parameters including lengths (a, b, c) and angles (alpha, beta, gamma). It assumes
    the CIF file contains only one dataset and extracts parameters from this dataset.

    Parameters
    ----------
    input_cif_path : Path
        The file path to the input CIF file. Can be a string path or a pathlib.Path
        object.

    Returns
    -------
    Tuple[List[str], Dict[str, float]]
        A tuple containing two elements:
        - A list of strings, each representing an element found in the chemical formula.
        - A dictionary with keys for cell parameter names ('a', 'b', 'c', 'alpha',
          'beta', 'gamma') and their respective values as floats.
    """

    # this read function also works with pathlib.Path objects
    cif_model = read_cif_safe(input_cif_path)

    # Get the first entry as a cif within QCrBox should only have the one
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    # We now how the entry will be named in unified cif
    formula_string = cif_block["_chemical_formula_sum"]
    # remove any numbers within the formula to isolate the elements
    for i in range(10):
        formula_string = formula_string.replace(str(i), " ")
    elements = formula_string.split()

    # get cell parameters by non-unified names
    cell_dict = {
        "a": float(cif_block["_cell_length_a"]),
        "b": float(cif_block["_cell_length_b"]),
        "c": float(cif_block["_cell_length_c"]),
        "alpha": float(cif_block["_cell_angle_alpha"]),
        "beta": float(cif_block["_cell_angle_beta"]),
        "gamma": float(cif_block["_cell_angle_gamma"]),
    }
    return elements, cell_dict


def cod_params(
    elements: List[str],
    cell_dict: Dict[str, float],
    cellpar_deviation: float,
    listed_elements_only: bool,
) -> Dict[str, float]:
    """
    Generate parameters for COD (Crystallography Open Database) REST API queries based
    on elements, cell parameters, and deviation tolerance.

    Parameters
    ----------
    elements : List[str]
        List of chemical element symbols.
    cell_dict : Dict[str, float]
        Dictionary with unit cell parameter names as keys and their values as floats.
    cellpar_deviation : float
        Allowed deviation fraction for cell parameters (e.g., 0.01 for 1% deviation).
    listed_elements_only : bool
        If True, limit the search to entries strictly containing the listed elements.

    Returns
    -------
    Dict[str, float]
        Parameters for COD REST API, including modified cell parameters and element
        list.

    """
    params = {f"el{i+1}": el for i, el in enumerate(elements)}

    if listed_elements_only:
        params["strictmax"] = len(elements)

    mult_low = 1 - cellpar_deviation
    mult_high = 1 + cellpar_deviation

    for append, mult in zip(("min", "max"), (mult_low, mult_high)):
        for var, val in cell_dict.items():
            params[f"{var[:3]}{append}"] = val * mult
    return params


def get_number_fitting_cod_entries(
    elements: List[str],
    cell_dict: Dict[str, float],
    cellpar_deviation: float,
    listed_elements_only: bool,
) -> int:
    """
    Get the count of COD entries fitting given criteria.

    Parameters
    ----------
    elements : List[str]
        List of chemical element symbols.
    cell_dict : Dict[str, float]
        Dictionary with unit cell parameter names as keys and their values as floats.
    cellpar_deviation : float
        Allowed deviation fraction for cell parameters.
    listed_elements_only : bool
        If True, limit the search to entries strictly containing the listed elements.

    Returns
    -------
    int
        The count of entries in the COD that match the criteria.

    """
    params = cod_params(elements, cell_dict, cellpar_deviation, listed_elements_only)
    params["format"] = "count"

    headers = {"content_type": "charset=utf-8"}

    result = requests.request("GET", COD_REST_URL, headers=headers, params=params, timeout=60)
    return int(result.text)


def get_celldiff_score(struc_dict: Dict[str, float], cell_dict: Dict[str, float]) -> float:
    """
    Calculate the cell difference score between two sets of cell parameters.

    Parameters
    ----------
    struc_dict : Dict[str, str]
        Dictionary with cell parameter names and their values for a structure.
    cell_dict : Dict[str, float]
        Dictionary with cell parameter names and target values for comparison.

    Returns
    -------
    float
        The sum of squared differences between structure and target cell parameters.

    """
    score = 0.0
    for var, val in cell_dict.items():
        score += (float(struc_dict[var]) - val) ** 2
    return score


def get_fitting_cod_entries(
    elements: List[str],
    cell_dict: Dict[str, float],
    cellpar_deviation: float,
    listed_elements_only: bool,
) -> List[Dict]:
    """
    Retrieve and sort COD entries fitting given criteria by their cell difference score.

    Parameters
    ----------
    elements : List[str]
        List of chemical element symbols.
    cell_dict : Dict[str, float]
        Dictionary with unit cell parameter names as keys and their values as floats.
    cellpar_deviation : float
        Allowed deviation fraction for cell parameters.
    listed_elements_only : bool
        If True, limit the search to entries strictly containing the listed elements.

    Returns
    -------
    List[Dict]
        Sorted list of COD entries based on the cell difference score.

    """
    params = cod_params(elements, cell_dict, cellpar_deviation, listed_elements_only)
    params["format"] = "json"

    headers = {"content_type": "application/json"}

    result = requests.request("GET", COD_REST_URL, headers=headers, params=params, timeout=60)

    entries = result.json()

    return list(sorted(entries, key=lambda x: get_celldiff_score(x, cell_dict)))


def download_cod_cif(cod_id: int, output_path: Path, timeout: int = 600) -> None:
    """
    Downloads a CIF file from the Crystallography Open Database (COD) for a specified
    entry ID and saves it to a designated location. Please be nice using this function.
    If you want to download the COD in its entirety, there are far better options listed
    on the COD website.

    Parameters
    ----------
    cod_id : int
        The unique identifier for the entry in the COD database to be downloaded.
    output_path : Path
        The path (including filename) where the CIF file will be saved. This can be
        provided as a string or a Path object.
    timeout : int, optional
        The maximum time in seconds to wait for the server to send data before giving
        up, by default 600 seconds.

    Returns
    -------
    None

    Raises
    ------
    requests.exceptions.RequestException
        Raised for issues like connectivity problems, timeouts, or HTTP errors during
        the download process.
    """
    url = f"https://www.crystallography.net/cod/{cod_id}.cif"

    result = requests.get(url, allow_redirects=True, timeout=timeout)

    with Path(output_path).open("wb") as fobj:
        fobj.write(result.content)
