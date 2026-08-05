import numpy as np
from iotbx.cif.model import block, cif
from fractions import Fraction
from typing import Tuple
import subprocess
import re
import shutil
import os
from pathlib import Path

from qcrboxtools.cif.read import cifdata_str_or_index, read_cif_safe, read_cif_as_unified
from qcrboxtools.cif.file_converter.tsc import read_tsc_file

YAML_PATH = "/opt/qcrbox/config_discamb-matts.yaml"


def symop_to_nosphera2(symop: str) -> str:
    """Clean and standardize a symmetry operation string to a NoSpherA2 format.

    Args:
        symop (str): Symmetry operation string.

    Returns
    -------
        str: Cleaned symmetry operation string.

    """
    symop = symop.replace(" ", "").upper()

    # Replace decimal fractions with proper fractions
    def replace_decimal_with_fraction(match):
        decimal_str = match.group(0)
        fraction = Fraction(decimal_str).limit_denominator(128)
        if fraction.denominator == 1:
            return str(fraction.numerator)
        else:
            return f"{fraction.numerator}/{fraction.denominator}"

    symop = re.sub(r"(?<!\d)(-?\d+\.\d+)(?!\d)", replace_decimal_with_fraction, symop)

    # make sure the fraction always comes first
    def change_fraction_operation_order(match):
        if match.group(2).startswith(("+", "-")):
            coordinate = match.group(2)
        else:
            coordinate = "+" + match.group(2)
        if match.group(3).startswith("+"):
            fraction = match.group(3)[1:]
        else:
            fraction = match.group(3)
        return match.group(1) + fraction + coordinate

    # replace X+1/2 with 1/2+X
    symop = re.sub(r"(^|,)([\-\+]?[XYZ])([\+\-]\d+/\d+)", change_fraction_operation_order, symop)

    # replace X with +X
    symop = re.sub(r"(^|,)([XYZ])", r"\1+\2", symop)
    return symop

def write_mock_hkl(filename, refln_dict):
    with open(filename, 'w') as fobj:
        for h, k, l in zip(refln_dict['_refln_index_h'], refln_dict['_refln_index_k'], refln_dict['_refln_index_l']):
            fobj.write(f'{int(h): 4d}{int(k): 4d}{int(l): 4d}{0.0: 8.2f}{0.0: 8.2f}\n')

def write_nosphera2_cif(cif_block: block, output_cif: Path):
    """Convert an input CIF file to a NoSpherA2-compatible CIF file.

    Args:
        input_cif (Path): Path to the input CIF file.
    """
    symops = [symop_to_nosphera2(op) for op in cif_block["_space_group_symop_operation_xyz"]]

    new_block = cif_block.copy()
    loop_key = next(key for key in new_block.loop_keys() if key.startswith("_space_group_symop"))

    symop_loop = new_block.get_loop(loop_key)
    symop_loop.update_column("_space_group_symop_operation_xyz", symops)

    new_cif = cif({"tonosphera2": new_block})

    output_cif.write_text(str(new_cif), encoding="UTF-8")

def generate_aff(input_cif: str, output_cif_name: str) -> str:
    """Generate a tsc file from an input CIF file and export the resulting
    aspherical atomic form factors as a CIF file.

    Args:
        input_cif (Path): Path to the input CIF file.
        output_cif_name (str): Name of the CIF file to export the atomic form factors to.
    """

    input_cif_path = Path(input_cif)
    output_cif_path = input_cif_path.parent / output_cif_name

    work_folder = Path("./matts_work").absolute()
    work_folder.mkdir(parents=True, exist_ok=True)
    work_cif_path = work_folder / 'work.cif'

    cif_model = read_cif_safe(input_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    symops = [symop_to_nosphera2(op) for op in cif_block["_space_group_symop_operation_xyz"]]

    new_block = cif_block.copy()
    loop_key = next(key for key in new_block.loop_keys() if key.startswith("_space_group_symop"))
    symop_loop = new_block.get_loop(loop_key)
    symop_loop.update_column("_space_group_symop_operation_xyz", symops)

    new_cif = cif({"tomatts": new_block})
    work_cif_path.write_text(str(new_cif), encoding="UTF-8")

    if "_refln_index_h" in cif_block:
        refln_entries = {
            f"_refln_index_{mil}": np.array(cif_block[ f"_refln_index_{mil}"]) for mil in ("h", "k", "l")
        }
    elif "_diffrn_refln_index_h" in cif_block:
        refln_entries = {
            f"_refln_index_{mil}": np.array(cif_block[ f"_diffrn_refln_index_{mil}"]) for mil in ("h", "k", "l")
        }
    else: 
        raise ValueError("No refln loop in cif (report as issue this should not have happened)")

    work_hkl = work_folder / "work.hkl"
    write_mock_hkl(work_hkl, refln_entries)

    log_file = work_folder / "discambMatts_cli.log"

    with log_file.open("w") as fobj:
        subprocess.run(["discambMATTS2tsc"], cwd=work_folder, stdout=fobj, check=True)

    tsc_path = work_cif_path.with_suffix(".tsc")

    if not tsc_path.exists():
        raise FileNotFoundError("discambMATTS2tsc did not produce the expected tsc file.")

    tsc_obj = read_tsc_file(tsc_path)

    structure_cif_block = read_cif_as_unified(input_cif_path, 0)

    new_block = tsc_obj.to_cif(
        structure_cif_block,
        "Discamb generated form factors from the MATTS database",
        "",
        "",
    )

    new_cif = cif()
    new_cif["tscblock"] = new_block
    with open(output_cif_path, "w", encoding="UTF-8") as output_tsc_cif:
        output_tsc_cif.write(str(new_cif))

    return str(output_cif_path)
    

    


