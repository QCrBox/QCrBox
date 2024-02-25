import argparse
import json
from pathlib import Path
from qcrboxtools.analyse.convergence import check_converged

def parse_optional_float(value):
    """
    Parses a string into a float or returns None if the string is 'None'.

    Args:
        value (str): A string representing a float or 'None'.

    Returns:
        float or None: The parsed float value or None.
    """
    return None if value.lower() == 'none' else float(value)

def main():
    parser = argparse.ArgumentParser(description='Check convergence of CIF datasets based on specified criteria.')
    parser.add_argument('cif1_path', type=Path, help='Path to the first CIF file.')
    parser.add_argument('cif1_dataset', help='Dataset index or name in the first CIF file.')
    parser.add_argument('cif2_path', type=Path, help='Path to the second CIF file.')
    parser.add_argument('cif2_dataset', help='Dataset index or name in the second CIF file.')
    parser.add_argument('--max_abs_position', type=parse_optional_float, help='Maximum absolute position difference allowed. Use "None" to skip.')
    parser.add_argument('--mean_abs_position', type=parse_optional_float, help='Mean absolute position difference allowed. Use "None" to skip.')
    parser.add_argument('--max_position_su', type=parse_optional_float, help='Maximum ratio of position difference to su allowed. Use "None" to skip.')
    parser.add_argument('--mean_position_su', type=parse_optional_float, help='Mean ratio of position difference to su allowed. Use "None" to skip.')
    parser.add_argument('--max_abs_uij', type=parse_optional_float, help='Maximum absolute difference in ADPs allowed. Use "None" to skip.')
    parser.add_argument('--mean_abs_uij', type=parse_optional_float, help='Mean absolute difference in ADPs allowed. Use "None" to skip.')
    parser.add_argument('--max_uij_su', type=parse_optional_float, help='Maximum ratio of ADP difference to su allowed. Use "None" to skip.')
    parser.add_argument('--mean_uij_su', type=parse_optional_float, help='Mean ratio of ADP difference to su allowed. Use "None" to skip.')
    parser.add_argument('--output', type=Path, required=True, help='Path to output JSON file.')

    args = parser.parse_args()

    cif1_dataset = int(args.cif1_dataset) if args.cif1_dataset.isdigit() else args.cif1_dataset
    cif2_dataset = int(args.cif2_dataset) if args.cif2_dataset.isdigit() else args.cif2_dataset

    criteria = {
        'max abs position': args.max_abs_position,
        'mean abs position': args.mean_abs_position,
        'max position/su': args.max_position_su,
        'mean position/su': args.mean_position_su,
        'max abs uij': args.max_abs_uij,
        'mean abs uij': args.mean_abs_uij,
        'max uij/su': args.max_uij_su,
        'mean uij/su': args.mean_uij_su
    }

    # Remove criteria set to None
    criteria = {k: v for k, v in criteria.items() if v is not None}

    is_converged = check_converged(
        args.cif1_path,
        cif1_dataset,
        args.cif2_path,
        cif2_dataset,
        criteria
    )

    result = {"converged": is_converged}
    with args.output.open('w') as f:
        json.dump(result, f)

    print(f'Convergence check: {"Converged" if is_converged else "Not converged"}')

if __name__ == "__main__":
    main()