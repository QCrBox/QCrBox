import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Tuple

import numpy as np
from iotbx.cif.model import block, cif
from qcrboxtools.cif.read import cifdata_str_or_index, read_cif_safe, read_cif_as_unified
from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml
from qcrboxtools.cif.file_converter.tsc import read_tsc_file

from itertools import product

NOSPHERA2_CMD = "/opt/qcrbox/bin/NoSpherA2"


def cell_constants_to_matrix(a: float, b: float, c: float, alpha: float, beta: float, gamma: float) -> np.ndarray:
    """
    Convert cell constants to a 3x3 cell matrix.

    Parameters
    ----------
    a : float
        Cell length a in Angstrom.
    b : float
        Cell length b in Angstrom.
    c : float
        Cell length c in Angstrom.
    alpha : float
        Cell angle alpha in degrees.
    beta : float
        Cell angle beta in degrees.
    gamma : float
        Cell angle gamma in degrees.

    Returns
    -------
    np.ndarray
        The 3x3 cell matrix.

    """
    alpha_rad = np.radians(alpha)
    beta_rad = np.radians(beta)
    gamma_rad = np.radians(gamma)

    cos_alpha = np.cos(alpha_rad)
    cos_beta = np.cos(beta_rad)
    cos_gamma = np.cos(gamma_rad)
    sin_gamma = np.sin(gamma_rad)

    matrix = np.zeros((3, 3))
    matrix[0, 0] = a
    matrix[0, 1] = b * cos_gamma
    matrix[0, 2] = c * cos_beta
    matrix[1, 1] = b * sin_gamma
    matrix[1, 2] = c * (cos_alpha - cos_beta * cos_gamma) / sin_gamma
    matrix[2, 2] = c * np.sqrt(1 - cos_beta**2 - ((cos_alpha - cos_beta * cos_gamma) / sin_gamma) ** 2)

    return matrix


def block2xyz(cif_block: block, disorder_groups: tuple[int] | None = None) -> str:
    """
    Convert a CIF block to an XYZ file format string.

    Parameters
    ----------
    cif_block : block
        The CIF block to convert.
    disorder_groups : Optional[Tuple[int]], optional
        Tuple of disorder group numbers to include in addition to the non-disordered atoms.
        If None, includes all only non-disordered atoms. Default is None.

    Returns
    -------
    str
        The XYZ file format string.

    """
    cell_a = float(cif_block["_cell_length_a"])
    cell_b = float(cif_block["_cell_length_b"])
    cell_c = float(cif_block["_cell_length_c"])
    alpha = float(cif_block["_cell_angle_alpha"])
    beta = float(cif_block["_cell_angle_beta"])
    gamma = float(cif_block["_cell_angle_gamma"])

    cell_matrix = cell_constants_to_matrix(cell_a, cell_b, cell_c, alpha, beta, gamma)

    disorder_groups = disorder_groups or tuple([])

    stringified_group = tuple(list(str(num) for num in disorder_groups) + [".", "?"])
    if (len(disorder_groups) > 0) and ("_atom_site_disorder_group" not in cif_block):
        raise ValueError("Disorder group specified but '_atom_site_disorder_group' not in CIF block.")
    if "_atom_site_disorder_group" not in cif_block:
        include = np.full(len(cif_block["_atom_site_type_symbol"]), True, dtype=bool)
    else:
        include = np.isin(np.array(cif_block["_atom_site_disorder_group"]), stringified_group)

    atom_types = np.array(cif_block["_atom_site_type_symbol"])[include]
    fract_x = np.array([float(val) for val in cif_block["_atom_site_fract_x"]])[include]
    fract_y = np.array([float(val) for val in cif_block["_atom_site_fract_y"]])[include]
    fract_z = np.array([float(val) for val in cif_block["_atom_site_fract_z"]])[include]
    xyz_fract = np.stack((fract_x, fract_y, fract_z), axis=-1)
    xyz_cart = np.einsum("xy,zy->zx", cell_matrix, xyz_fract)

    n_atoms = len(atom_types)

    atom_lines = [f"{atom_type} {x:.9f} {y:.9f} {z:.9f}" for atom_type, (x, y, z) in zip(atom_types, xyz_cart, strict=False)]
    atom_line_string = "\n".join(atom_lines)

    return f"{n_atoms}\nCreated-xyz\n{atom_line_string}\n\n"


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


def write_xyz(cif_block: block, output_xyz: Path, disorder_groups: tuple[int] | None = None):
    """Extract atomic coordinates from a CIF block and write them to an XYZ file.

    Args:
        cif_block (block): CIF block containing atomic coordinates.
        output_xyz (Path): Path to the output XYZ file.
    """
    xyz_content = block2xyz(cif_block, disorder_groups)
    output_xyz.write_text(xyz_content, encoding="UTF-8")


def _has_known_value(cif_block: block, key: str) -> bool:
    """Check whether a scalar CIF entry is present and not the CIF 'unknown' placeholder ('?')."""
    return key in cif_block and str(cif_block[key]).strip() != "?"


def block_to_resolution_info(cif_block: block) -> Tuple[str, ...]:
    """Extract resolution information from a CIF block.

    Args:
        cif_block (block): CIF block containing resolution information.
    Returns:
        Tuple[str, ...]: Tuple of resolution information strings.
    """
    if all(_has_known_value(cif_block, key) for key in (
        "_diffrn_reflns_limit_h_min", "_diffrn_reflns_limit_h_max",
        "_diffrn_reflns_limit_k_min", "_diffrn_reflns_limit_k_max",
        "_diffrn_reflns_limit_l_min", "_diffrn_reflns_limit_l_max"
    )):
        return (
            "-hkl_min_max",
            str(cif_block["_diffrn_reflns_limit_h_min"]),
            str(cif_block["_diffrn_reflns_limit_h_max"]),
            str(cif_block["_diffrn_reflns_limit_k_min"]),
            str(cif_block["_diffrn_reflns_limit_k_max"]),
            str(cif_block["_diffrn_reflns_limit_l_min"]),
            str(cif_block["_diffrn_reflns_limit_l_max"]),
        )
    elif _has_known_value(cif_block, "_reflns_d_resolution_high"):
        return ("-dmin", str(cif_block["_reflns_d_resolution_high"]))
    elif all(_has_known_value(cif_block, key) for key in ("_diffrn_reflns_theta_max", "_diffrn_radiation_wavelength")):
        theta_max = float(cif_block["_diffrn_reflns_theta_max"])
        wavelength = float(cif_block["_diffrn_radiation_wavelength"])
        dmin = wavelength / (2 * np.sin(np.radians(theta_max)))
        return ("-dmin", f"{dmin:.4f}")
    elif all(key in cif_block for key in ("_diffrn_refln_index_h", "_diffrn_refln_index_k", "_diffrn_refln_index_l")):
        h_vals = [int(mil_h) for mil_h in cif_block["_diffrn_refln_index_h"]]
        k_vals = [int(mil_k) for mil_k in cif_block["_diffrn_refln_index_k"]]
        l_vals = [int(mil_l) for mil_l in cif_block["_diffrn_refln_index_l"]]
        h_min, h_max = min(h_vals), max(h_vals)
        k_min, k_max = min(k_vals), max(k_vals)
        l_min, l_max = min(l_vals), max(l_vals)
        return (
            "-hkl_min_max",
            str(h_min), str(h_max),
            str(k_min), str(k_max),
            str(l_min), str(l_max),
        )
    elif all(key in cif_block for key in ("_refln_index_h", "_refln_index_k", "_refln_index_l")):
        h_vals = [int(mil_h) for mil_h in cif_block["_refln_index_h"]]
        k_vals = [int(mil_k) for mil_k in cif_block["_refln_index_k"]]
        l_vals = [int(mil_l) for mil_l in cif_block["_refln_index_l"]]
        h_min, h_max = min(h_vals), max(h_vals)
        k_min, k_max = min(k_vals), max(k_vals)
        l_min, l_max = min(l_vals), max(l_vals)
        return (
            "-hkl_min_max",
            str(h_min), str(h_max),
            str(k_min), str(k_max),
            str(l_min), str(l_max),
        )
    else:
        raise ValueError("No resolution information found in CIF block. This means cif generation in QCrBox is buggy.")


def call_nosphera2_ptb_single(work_folder: Path, xtb_file: Path, cif_block: block):
    """Call NoSpherA2 with PTB to generate a tsc file.

    Args:
        xtb_file (Path): Path to the input XTB file.
        cif_file (Path): Path to the input CIF file.
    """
    nph2_cif_path = work_folder / "input_nosphera2.cif"
    write_nosphera2_cif(cif_block, nph2_cif_path)

    res_info = block_to_resolution_info(cif_block)

    subprocess.run(
        [
            NOSPHERA2_CMD, "-wfn", str(xtb_file), "-cif", str(nph2_cif_path), "-ECP", "3",
            *res_info
        ], check=True, cwd=work_folder
    )

def generate_wfn_names(disorder_groups: tuple[tuple[int, ...], ...]) -> list[str]:
    """Generate a list of wavefunction file names based on disorder groups.

    Args:
        disorder_groups (tuple[tuple[int, ...], ...]): Tuple of tuples representing disorder groups.

    Returns:
        list[str]: List of wavefunction file names.
    """
    wfn_names = []
    for group in disorder_groups:
        group_str = "_".join(str(num) for num in group) if len(group) > 0 else "no_disorder"
        wfn_names.append(f"wfn_{group_str}.xtb")
    return wfn_names

def call_nosphera2_ptb_disorder(work_folder: Path, xtb_files: list[Path], cif_block: block, disorder_groups: tuple[tuple[int, ...], ...]):
    """Call NoSpherA2 with PTB to generate a tsc file for disordered structures.

    Args:
        xtb_files (list[Path]): List of paths to the input XTB files.
        cif_file (Path): Path to the input CIF file.
        disorder_groups (list[tuple[int]]): List of tuples representing disorder groups.
    """
    nph2_cif_path = work_folder / "input_nosphera2.cif"
    write_nosphera2_cif(cif_block, nph2_cif_path)

    res_info = block_to_resolution_info(cif_block)

    mtc_args = ['-mtc']
    for xtb_file, group in zip(xtb_files, disorder_groups):
        group_str = ",".join(str(num) for num in group)
        mtc_args.extend([str(xtb_file), group_str])

    subprocess.run(
        [
            NOSPHERA2_CMD, "-cif", str(nph2_cif_path), "-ECP", "3",
            *mtc_args,
            *res_info
        ], check=True, cwd=work_folder
    )

def generate_group_of_disorder_groups(disorder_groups_str: str) -> tuple[tuple[int, ...], ...]:
    """Generate a tuple of tuples representing all combinations of disorder groups. That 
    can occur with the combination of independent disorder groups given.

    Args:
        disorder_groups_str (str): Comma separated lists of disorder groups that are in turn separated
            by semicolons. E.g. '1,2;3,4' says that groups 1 and 2 are mutually exclusive and 3 and 4 are mutually
            exclusive, but either can be combined with the other groups
    Returns:
        tuple[tuple[int, ...], ...]: Tuple of tuples representing all combinations of disorder groups.
    """
    if disorder_groups_str.lower() == "none":
        return ((),)
    independent_group_strs = disorder_groups_str.split(";")
    if len(independent_group_strs) == 0 or (len(independent_group_strs) == 1 and independent_group_strs[0].strip() == ""):
        return ((),)
    groups = []

    for group_str in independent_group_strs:
        new_group = []
        for split in group_str.split(','):
            if split.strip() == "":
                continue
            match = re.match(r"(-?\d)+-(-?\d+)", split)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                new_group.extend(list(range(start, end+1)))
            else:
                new_group.append(int(split))
        if len(new_group) > 0:
            groups.append(tuple(new_group))
    return tuple(product(*groups))

def generate_aff(input_cif: str, disorder_groups: str, output_cif_name: str) -> str:
    """Generate a tsc file from an input CIF file and export the resulting
    aspherical atomic form factors as a CIF file.

    Args:
        input_cif (Path): Path to the input CIF file.
        disorder_groups (str): Disorder group specification, see generate_group_of_disorder_groups.
        output_cif_name (str): Name of the CIF file to export the atomic form factors to.
    """
    input_cif_path = Path(input_cif)
    output_cif_path = input_cif_path.parent / output_cif_name

    work_folder = Path("./nosphera2_ptb_work").absolute()
    work_folder.mkdir(parents=True, exist_ok=True)

    generated_disorder_groups = generate_group_of_disorder_groups(disorder_groups)

    cif_model = read_cif_safe(input_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    wfn_file_names = generate_wfn_names(generated_disorder_groups)

    for group, wfn_file_name in zip(generated_disorder_groups, wfn_file_names):
        # Step 1: Convert CIF to XYZ
        wfn_path = work_folder / wfn_file_name
        xyz_file = wfn_path.with_suffix(".xyz")
        write_xyz(cif_block, xyz_file, disorder_groups=group if len(group) > 0 else None)

        # Step 2: Call PTB to generate density
        subprocess.run(
            [
                "ptb",
                str(xyz_file),
                "-bas",
                "/opt/qcrbox/bin/.basis_vDZP",
                "-par",
                "/opt/qcrbox/bin/.atompara",
                "-stda",
            ],
            cwd=work_folder,
        )
        shutil.move(work_folder / "wfn.xtb", wfn_path)

    if len(wfn_file_names) == 1:
        # Step 2: Call NoSpherA2 to generate tsc
        call_nosphera2_ptb_single(work_folder, work_folder / wfn_file_names[0], cif_block)
    else:
        call_nosphera2_ptb_disorder(
            work_folder, 
            [work_folder / name for name in wfn_file_names], 
            cif_block, 
            generated_disorder_groups
        )
    generated_tscb = work_folder / "experimental.tscb"
    labelled_tsc = work_folder / "labelled.tsc"
    nph2_cif_path = work_folder / "input_nosphera2.cif"

    subprocess.run([
        "NoSpherA2", "-tsc_labels", str(generated_tscb), str(nph2_cif_path),  str(labelled_tsc)
    ])

    if not labelled_tsc.exists():
        raise FileNotFoundError("NoSpherA2 did not produce the expected tsc file.")

    # Export the aspherical atomic form factors as a CIF file, following the same
    # _aspheric_ff/_wfn_moiety schema produced by xharpy_gpaw's atom_form_fact_gpaw.
    tsc_obj = read_tsc_file(labelled_tsc)
    structure_cif_block = read_cif_as_unified(input_cif_path, 0)
    new_block = tsc_obj.to_cif(
        structure_cif_block,
        "PTB density partitioned by NoSpherA2",
        "hirshfeld",
        "NoSpherA2",
    )
    new_block.add_data_item("_wfns.software", "PTB")
    new_block.add_data_item("_wfns.type", "semiempirical")
    new_block.add_data_item("_wfns.method", "PTB")

    new_cif = cif()
    new_cif["tsclock"] = new_block
    with open(output_cif_path, "w", encoding="UTF-8") as output_tsc_cif:
        output_tsc_cif.write(str(new_cif))

    # Clean up
    shutil.rmtree(work_folder)
    return str(output_cif_path)
