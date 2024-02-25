# Copyright 2024 Paul Niklas Ruth.
# SPDX-License-Identifier: MPL-2.0

"""
This script provides a command-line interface for combining CIF (Crystallographic
Information File) files. Whereas one cif file provides the cell information, the
reflections etc. The second cif file provides the structure. This enables the
refinement against repeat measurements, be it with different diffraction sources
or with different experimental conditions.

Arguments:
- cif_path: Path to the destination CIF file.
- cif_dataset: Name of the dataset in the destination CIF file.
- structure_cif_path: Path to the source CIF file.
- structure_cif_dataset: Name of the dataset in the source CIF file.
- output_cif_path: Path for the combined output CIF file (optional).

The script processes these arguments and calls `replace_structure_from_cif` with the
appropriate parameters.
"""

import argparse

from qcrboxtools.cif.merge import replace_structure_from_cif

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='QCrBoxTools cif cli',
        description='combine cifs via module call'
    )

    parser.add_argument(
        'cif_path',
        help="Path to cif file where the structure is copied TO"
    )
    parser.add_argument(
        'cif_dataset',
        help="Name of dataset in cif file where the structure is copied TO"
    )

    parser.add_argument(
        'structure_cif_path',
        help="Path to cif file where the structure is copied FROM"
    )

    parser.add_argument(
        'structure_cif_dataset',
        help="Name of dataset in cif file where the structure is copied FROM"
    )

    parser.add_argument(
        '--output_cif_path',
        help="Path to where the combined output cif will be written (default: cif_path)",
        default=None
    )

    args = parser.parse_args()

    if args.output_cif_path is None:
        output_cif_path = args.cif_path
    else:
        output_cif_path = args.output_cif_path

    try:
        cif_dataset = int(args.cif_dataset)
    except ValueError:
        cif_dataset = args.cif_dataset

    try:
        structure_cif_dataset = int(args.structure_cif_dataset)
    except ValueError:
        structure_cif_dataset = args.structure_cif_dataset

    replace_structure_from_cif(
        args.cif_path,
        cif_dataset,
        args.structure_cif_path,
        structure_cif_dataset,
        output_cif_path
    )
