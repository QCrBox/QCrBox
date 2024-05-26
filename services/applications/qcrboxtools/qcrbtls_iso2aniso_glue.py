import argparse
from pathlib import Path
from typing import List, Optional

from qcrboxtools.cif.cif2cif import cif_file_merge_to_unified_by_yml, cif_file_to_specific_by_yml
from qcrboxtools.cif.iso2aniso import cif_iso2aniso

YML_PATH = "/opt/qcrbox/config_qcrboxtools.yaml"


def parse_args_to_none(value: str) -> Optional[List[str]]:
    """
    Parse argument string to None if it is 'None'.

    Parameters
    ----------
    value : str
        Input argument string.

    Returns
    -------
    Optional[List[str]]
        None if the input is 'None', otherwise returns a list of strings.
    """
    if value.lower() == "none":
        return None
    return value.split(",")


def main():
    parser = argparse.ArgumentParser(
        description="Convert isotropic displacement parameters to anisotropic in a CIF file."
    )

    # Required arguments
    parser.add_argument("input_cif_path", type=Path, help="Path to the input CIF file.")
    parser.add_argument("output_cif_path", type=Path, help="Path to the output CIF file.")

    # Optional arguments
    parser.add_argument(
        "--select_names",
        type=parse_args_to_none,
        default=None,
        help="Specific atom names to convert, separated by commas. Use 'None' to ignore.",
    )
    parser.add_argument(
        "--select_elements",
        type=parse_args_to_none,
        default=None,
        help="Specific elements to convert, separated by commas. Use 'None' to ignore.",
    )
    parser.add_argument(
        "--select_regexes",
        type=parse_args_to_none,
        default=None,
        help="Regex patterns to match atom names for conversion, separated by commas. Use 'None' to ignore.",
    )
    parser.add_argument(
        "--overwrite",
        type=bool,
        default=False,
        help="Overwrite existing anisotropic parameters if True.",
    )

    args = parser.parse_args()

    input_cif_path = args.input_cif_path
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(input_cif_path, work_cif_path, YML_PATH, "iso2aniso", "input_cif_path")

    # Call the function with parsed arguments
    cif_iso2aniso(
        input_cif_path=work_cif_path,
        cif_dataset="0",
        output_cif_path=work_cif_path,
        select_names=args.select_names,
        select_elements=args.select_elements,
        select_regexes=args.select_regexes,
        overwrite=args.overwrite,
    )

    cif_file_merge_to_unified_by_yml(
        work_cif_path, args.output_cif_path, input_cif_path, YML_PATH, "iso2aniso", "output_cif_path"
    )


if __name__ == "__main__":
    main()
