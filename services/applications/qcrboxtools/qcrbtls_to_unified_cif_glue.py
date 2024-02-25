import argparse
from pathlib import Path
from typing import Optional, List, Union
from qcrboxtools.cif.cif2cif import cif_file_unify_split  # Adjust import path as necessary

def main():
    parser = argparse.ArgumentParser(description="Process CIF files with optional modifications.")
    parser.add_argument("input_cif_path", type=str, help="The input CIF file path.")
    parser.add_argument("output_cif_path", type=str, help="The output file path for the processed CIF.")
    parser.add_argument("--convert_keywords", action="store_true", default=True,
                        help="If set, converts keywords to a unified format. Enabled by default.")
    parser.add_argument("--no-convert_keywords", dest="convert_keywords", action="store_false",
                        help="If set, does not convert keywords to a unified format.")
    parser.add_argument("--custom_categories", type=str, nargs="*", default=None,
                        help="Custom categories for keyword conversion, if applicable. " +
                        "Provide as space-separated list.")
    parser.add_argument("--split_sus", action="store_true", default=True,
                        help="If set, splits values from their SUs in the CIF content. Enabled by default.")
    parser.add_argument("--no-split_sus", dest="split_sus", action="store_false",
                        help="If set, does not split values from their SUs in the CIF content.")

    args = parser.parse_args()

    # Convert custom_categories from space-separated list to a Python list (if not None)
    custom_categories: Optional[List[str]] = args.custom_categories if args.custom_categories is not None else None

    # Call the cif_file_unify_split function with the parsed arguments
    cif_file_unify_split(
        input_cif_path=Path(args.input_cif_path),
        output_cif_path=Path(args.output_cif_path),
        convert_keywords=args.convert_keywords,
        custom_categories=custom_categories,
        split_sus=args.split_sus
    )

if __name__ == "__main__":
    main()
