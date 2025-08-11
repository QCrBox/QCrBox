import argparse
import json
from pathlib import Path

from qcrboxtools.analyse.convergence import check_converged
from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml

YML_PATH = "/opt/qcrbox/config_qcrboxtools.yaml"


def check_structure_convergence(cif1, cif2, output_json_path):
    # Convert paths in Path objects and CIFs into unified format
    cif1 = Path(cif1)
    cif2 = Path(cif2)
    converted1_path = cif1.parent / "converted1.cif"
    converted2_path = cif2.parent / "converted2.cif"
    cif_file_to_specific_by_yml(cif1, converted1_path, YML_PATH, "check_structure_convergence", "cif1")
    cif_file_to_specific_by_yml(cif2, converted2_path, YML_PATH, "check_structure_convergence", "cif2")

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


def parse_optional_float(value) -> None | float:
    """
    Parses a string into a float or returns None if the string is 'None'.

    Args:
        value (str): A string representing a float or 'None'.

    Returns:
        float or None: The parsed float value or None.
    """
    return None if value.lower() == "none" else float(value)


def main():
    parser = argparse.ArgumentParser(description="Check convergence of CIF datasets based on specified criteria.")
    parser.add_argument("cif1_path", type=Path, help="Path to the first CIF file.")
    parser.add_argument("cif1_dataset", help="Dataset index or name in the first CIF file.")
    parser.add_argument("cif2_path", type=Path, help="Path to the second CIF file.")
    parser.add_argument("cif2_dataset", help="Dataset index or name in the second CIF file.")
    parser.add_argument(
        "--max_abs_position",
        type=parse_optional_float,
        help='Maximum absolute position difference allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--mean_abs_position",
        type=parse_optional_float,
        help='Mean absolute position difference allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--max_position_su",
        type=parse_optional_float,
        help='Maximum ratio of position difference to su allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--mean_position_su",
        type=parse_optional_float,
        help='Mean ratio of position difference to su allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--max_abs_uij",
        type=parse_optional_float,
        help='Maximum absolute difference in ADPs allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--mean_abs_uij",
        type=parse_optional_float,
        help='Mean absolute difference in ADPs allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--max_uij_su",
        type=parse_optional_float,
        help='Maximum ratio of ADP difference to su allowed. Use "None" to skip.',
    )
    parser.add_argument(
        "--mean_uij_su",
        type=parse_optional_float,
        help='Mean ratio of ADP difference to su allowed. Use "None" to skip.',
    )
    parser.add_argument("--output", type=Path, required=True, help="Path to output JSON file.")

    args = parser.parse_args()

    converted1_path = args.cif1_path.parent / "converted1.cif"

    converted2_path = args.cif2_path.parent / "converted2.cif"

    cif_file_to_specific_by_yml(args.cif1_path, converted1_path, YML_PATH, "check_structure_convergence", "cif1_path")

    cif_file_to_specific_by_yml(args.cif2_path, converted2_path, YML_PATH, "check_structure_convergence", "cif2_path")

    criteria = {
        "max abs position": args.max_abs_position,
        "mean abs position": args.mean_abs_position,
        "max position/su": args.max_position_su,
        "mean position/su": args.mean_position_su,
        "max abs uij": args.max_abs_uij,
        "mean abs uij": args.mean_abs_uij,
        "max uij/su": args.max_uij_su,
        "mean uij/su": args.mean_uij_su,
    }

    # Remove criteria set to None
    criteria = {k: v for k, v in criteria.items() if v is not None}

    is_converged = check_converged(converted1_path, args.cif1_dataset, converted2_path, args.cif2_dataset, criteria)

    # clean up the converted structure
    converted1_path.unlink()
    converted2_path.unlink()

    result = {"converged": is_converged}
    with args.output.open("w") as f:
        json.dump(result, f)

    print(f'Convergence check: {"Converged" if is_converged else "Not converged"}')


if __name__ == "__main__":
    main()
