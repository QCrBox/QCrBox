from collections import namedtuple
from pathlib import Path
from textwrap import dedent
from typing import List, Tuple

import numpy as np
import plotly.graph_objects as go
import trimesh
from bokeh.embed import file_html
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from cctbx.crystal.distance_based_connectivity import build_simple_two_way_bond_sets
from iotbx import cif
from iotbx.cif import reader
from qcrboxtools.analyse.quality.cif import from_entry
from qcrboxtools.analyse.quality.html.quality_box import (
    QualityIndicatorBox,
    quality_div_group,
)
from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml
from qcrboxtools.cif.read import cifdata_str_or_index, read_cif_safe
from scitbx.array_family import flex

YAML_PATH = "config_qcrbox_quality.yaml"


def basic_model_quality_indicators(input_cif_path, output_html_path):
    input_cif_path = Path(input_cif_path)
    output_html_path = Path(output_html_path)

    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(
        input_cif_path,
        work_cif_path,
        YAML_PATH,
        "basic_model_quality_indicators",
        "input_cif_path",
    )

    cif_model = read_cif_safe(work_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    indicators = [
        QualityIndicatorBox(
            name=r"$R_1(F)$",
            value=str(float(cif_block["_refine_ls.r_factor_all"]) * 100),
            unit="%",
            quality_level=from_entry(cif_block, "_refine_ls.r_factor_all"),
        ),
        QualityIndicatorBox(
            name=r"$wR_2(F^2)$",
            value=str(float(cif_block["_refine_ls.wr_factor_gt"]) * 100),
            unit="%",
            quality_level=from_entry(cif_block, "_refine_ls.wr_factor_gt"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{max}$",
            value=cif_block["_refine.diff_density_max"],
            unit=r"$e\,\AA^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_max"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{min}$",
            value=cif_block["_refine.diff_density_min"],
            unit=r"$e\,\AA^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_min"),
        ),
        QualityIndicatorBox(
            name=r"$d_\mathrm{min}$",
            value=cif_block["_refine_ls.d_res_high"],
            unit=r"$\AA$",
            quality_level=from_entry(cif_block, "_refine_ls.d_res_high"),
        ),
        QualityIndicatorBox(
            name="GooF",
            value=cif_block["_refine_ls.goodness_of_fit_ref"],
            unit="",
            quality_level=from_entry(cif_block, "_refine_ls.goodness_of_fit_ref"),
        ),
    ]

    boxes_css = dedent(
        """
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }

        .container {
            display: flex;
            gap: 10px;
        }

        .indicator {
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            width: 120px;
            color: white;
        }

        /* Data Quality Colour Classes */
        .data-quality-good {
            background-color: #00821e;
            color: #ffffff;
        }

        .data-quality-goodish {
            background-color: #6fc936;
            color: #000000;
        }

        .data-quality-marginal {
            background-color: #dfee14;
            color: #000000;
        }

        .data-quality-badish {
            background-color: #FF9800;
            color: #000000;
        }

        .data-quality-bad {
            background-color: #ee3a14;
            color: #ffffff;
        }

        .data-quality-information {
            background-color: #6b6b6b;
            color: #ffffff;
        }

        /* Indicator Content */
        .indicator .name {
            font-weight: bold;
        }
    """
    ).strip()

    output_html_path.write_text(quality_div_group(indicators), encoding="UTF-8")
    output_html_path.with_suffix(".css").write_text(boxes_css, encoding="UTF-8")


def fobs_calc_block_from_cif(input_cif_path: Path):
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(
        input_cif_path,
        work_cif_path,
        YAML_PATH,
        "fobs_div_fcalc",
        "input_cif_path",
    )

    cif_model = read_cif_safe(work_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)
    if "_iucr.refine_fcf_details" in cif_block:
        cif_model = reader(input_string=cif_block["_iucr.refine_fcf_details"]).model()
        cif_block, _ = cifdata_str_or_index(cif_model, 0)

    return cif_block


def diagonal_line_parameters(fobs, fcalc):
    max_f = max((np.max(fobs), np.max(fcalc)))
    min_f = min((np.min(fobs), np.min(fcalc)))
    add_f = 0.05 * (max_f - min_f)
    line_start_end = [min_f - 100 * add_f, max_f + 100 * add_f]
    view_range = [min_f - add_f, max_f + add_f]
    return line_start_end, view_range


def create_hkl_labels(cif_block):
    miller_entries = [f"_refln_index_{i}" for i in ("h", "k", "l")]
    if all(entry in cif_block for entry in miller_entries):
        miller_content = list(cif_block[entry] for entry in miller_entries)
        return [f"({mil_h} {mil_k} {mil_l})" for mil_h, mil_k, mil_l in zip(*miller_content)]
    return None


def fobs_div_fcalc_plotly(input_cif_path, output_html_path):
    input_cif_path = Path(input_cif_path)
    output_html_path = Path(output_html_path)

    cif_block = fobs_calc_block_from_cif(input_cif_path)

    f_calc_sq = np.array(cif_block["_refln_F_squared_calc"], dtype=np.float64)
    f_obs_sq = np.array(cif_block["_refln_F_squared_meas"], dtype=np.float64)

    fobs = np.sqrt(f_obs_sq)
    fcalc = np.sqrt(f_calc_sq)

    line_start_end, view_range = diagonal_line_parameters(fobs, fcalc)
    miller_labels = create_hkl_labels(cif_block)

    if miller_labels is None:
        hovertemplate = None
    else:
        hovertemplate = "%{text}"
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=fobs, y=fcalc, hovertemplate=hovertemplate, name="hkl", text=miller_labels, mode="markers")
    )

    fig.add_trace(
        go.Scatter(
            x=line_start_end,
            y=line_start_end,
            mode="lines",
            line=dict(color="rgba(0,0,0,0.2)", width=1),
        )
    )

    fig.update_layout(
        xaxis_title=r"$$F_\text{obs}$$",
        yaxis_title=r"$$F_\text{calc}$$",
    )

    fig.update_xaxes(range=view_range)
    fig.update_yaxes(range=view_range)
    fig.update_layout(showlegend=False)

    html_string = fig.to_html(include_plotlyjs=True, include_mathjax="cdn")

    output_html_path.write_text(html_string, encoding="UTF-8")


def fobs_div_fcalc_bokeh(input_cif_path, output_html_path):
    input_cif_path = Path(input_cif_path)
    output_html_path = Path(output_html_path)

    cif_block = fobs_calc_block_from_cif(input_cif_path)

    f_calc_sq = np.array(cif_block["_refln_F_squared_calc"], dtype=np.float64)
    f_obs_sq = np.array(cif_block["_refln_F_squared_meas"], dtype=np.float64)

    fobs = np.sqrt(f_obs_sq)
    fcalc = np.sqrt(f_calc_sq)

    line_start_end, view_range = diagonal_line_parameters(fobs, fcalc)
    miller_labels = create_hkl_labels(cif_block)

    data_dict = {"Fobs": fobs, "Fcalc": fcalc}

    if miller_labels is None:
        tooltips = None
    else:
        data_dict["Miller"] = miller_labels
        tooltips = [("hkl", "@Miller")]

    source = ColumnDataSource(data=data_dict)

    p = figure(
        tooltips=tooltips,
        y_range=view_range,
        x_range=view_range,
        y_axis_label=r"$$F_\mathrm{calc}$$",
        x_axis_label=r"$$F_\mathrm{obs}$$",
    )
    p.scatter("Fobs", "Fcalc", source=source)
    p.line(line_start_end, line_start_end, line_width=1, color="#000000", alpha=0.2)
    html_string = file_html(p)

    output_html_path.write_text(html_string, encoding="UTF-8")


elements = [
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
]

radii = [
    0.31,
    0.28,
    1.28,
    0.96,
    0.85,
    0.76,
    0.71,
    0.66,
    0.57,
    0.58,
    1.66,
    1.41,
    1.21,
    1.11,
    1.07,
    1.05,
    1.02,
    1.06,
    2.03,
    1.76,
    1.70,
    1.60,
    1.53,
    1.39,
    1.39,
    1.32,
    1.26,
    1.24,
    1.32,
    1.22,
    1.22,
    1.20,
    1.19,
    1.20,
    1.20,
    1.16,
    2.20,
    1.95,
    1.90,
    1.75,
    1.64,
    1.54,
    1.47,
    1.46,
    1.42,
    1.39,
    1.45,
    1.44,
    1.42,
    1.39,
    1.39,
    1.38,
    1.39,
    1.40,
    2.44,
    2.15,
    2.07,
    2.04,
    2.03,
    2.01,
    1.99,
    1.98,
    1.98,
    1.96,
    1.94,
    1.92,
    1.92,
    1.89,
    1.90,
    1.87,
    1.87,
    1.75,
    1.70,
    1.62,
    1.51,
    1.44,
    1.41,
    1.36,
    1.36,
    1.32,
    1.45,
    1.46,
    1.48,
    1.40,
    1.50,
    1.50,
    2.60,
    2.21,
    2.15,
    2.06,
    2.00,
    1.96,
    1.90,
    1.87,
    1.80,
    1.69,
]

atom_colours = [
    "#ffffff",
    "#d9ffff",
    "#cc80ff",
    "#c2ff00",
    "#ffb5b5",
    "#000000",
    "#3050f8",
    "#ff0d0d",
    "#90e050",
    "#b3e3f5",
    "#ab5cf2",
    "#8aff00",
    "#bfa6a6",
    "#f0c8a0",
    "#ff8000",
    "#ffff30",
    "#1ff01f",
    "#80d1e3",
    "#8f40d4",
    "#3dff00",
    "#e6e6e6",
    "#bfc2c7",
    "#a6a6ab",
    "#8a99c7",
    "#9c7ac7",
    "#e06633",
    "#f090a0",
    "#50d050",
    "#c88033",
    "#7d80b0",
    "#c28f8f",
    "#668f8f",
    "#bd80e3",
    "#ffa100",
    "#a62929",
    "#5cb8d1",
    "#702eb0",
    "#00ff00",
    "#94ffff",
    "#94e0e0",
    "#73c2c9",
    "#54b5b5",
    "#3b9e9e",
    "#248f8f",
    "#0a7d8c",
    "#006985",
    "#c0c0c0",
    "#ffd98f",
    "#a67573",
    "#668080",
    "#9e63b5",
    "#d47a00",
    "#940094",
    "#429eb0",
    "#57178f",
    "#00c900",
    "#70d4ff",
    "#ffffc7",
    "#d9ffc7",
    "#c7ffc7",
    "#a3ffc7",
    "#8fffc7",
    "#61ffc7",
    "#45ffc7",
    "#30ffc7",
    "#1fffc7",
    "#00ff9c",
    "#00e675",
    "#00d452",
    "#00bf38",
    "#00ab24",
    "#4dc2ff",
    "#4da6ff",
    "#2194d6",
    "#267dab",
    "#266696",
    "#175487",
    "#d0d0e0",
    "#ffd123",
    "#b8b8d0",
    "#a6544d",
    "#575961",
    "#9e4fb5",
    "#ab5c00",
    "#754f45",
    "#428296",
    "#420066",
    "#007d00",
    "#70abfa",
    "#00baff",
    "#00a1ff",
    "#008fff",
    "#0080ff",
    "#006bff",
    "#545cf2",
    "#785ce3",
]

ring_colours = [
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#ffffff",
    "#ffffff",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#000000",
    "#ffffff",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#ffffff",
    "#ffffff",
    "#ffffff",
    "#ffffff",
    "#000000",
    "#ffffff",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#000000",
    "#ffffff",
    "#ffffff",
    "#ffffff",
]

ElementValues = namedtuple("ElementValues", ["radius", "atom_colour", "ring_colour"])

element_dict = {
    name: ElementValues(radius=radius, atom_colour=atom_colour, ring_colour=ring_colour)
    for name, radius, atom_colour, ring_colour in zip(elements, radii, atom_colours, ring_colours)
}


def cif_path2dict(cif_path: str, data_block_name: str = None) -> cif.model.block:
    """Read a CIF file and extract specified data block.

    Parameters
    ----------
    cif_path : str
        Path to the CIF file.
    data_block_name : str, optional
        Name of the data block to extract. If None, extracts first available
        data block or second if first is 'global'.

    Returns
    -------
    cif.model.block
        Representation of the extracted data block.

    Raises
    ------
    KeyError
        If CIF file contains multiple data blocks and data_block_name is not
        specified.
    """
    reader = cif.reader(cif_path)
    model = reader.model()
    if data_block_name is not None:
        return model[data_block_name]
    else:
        model_iter = iter(model.items())
        if len(model) == 1:
            return next(model_iter)
        elif len(model) == 2 and next(model_iter)[0] == "global":
            return next(model_iter)
        else:
            raise KeyError("cif file contains multiple data_block entries, but data_block_name is not specified")


def mean_plane2(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate mean plane normal vector using least squares.

    Parameters
    ----------
    points : np.ndarray
        Nx3 array of point coordinates.

    Returns
    -------
    np.ndarray
        Unit normal vector of the mean plane.
    np.ndarray
        Center point of the plane.
    """
    points = points.T
    centre = points.mean(axis=0)
    centred = points - centre
    A = np.concatenate((centred[:, :2], np.ones((points.shape[0], 1))), axis=1)
    b = centred[:, 2, np.newaxis]
    vector = np.linalg.inv(np.dot(A.T, A)) @ A.T @ b
    return vector[:, 0] / np.linalg.norm(vector), centre[:, None]


def mean_plane(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate mean plane normal vector using covariance matrix.

    Parameters
    ----------
    points : np.ndarray
        Nx3 array of point coordinates.

    Returns
    -------
    np.ndarray
        Unit normal vector of the mean plane.
    np.ndarray
        Center point of the plane.

    Notes
    -----
    Uses eigenvalue decomposition of the covariance matrix. Falls back to
    mean_plane2 if eigenvalue decomposition fails.
    """
    centre = points.mean(axis=0)
    centred = points - centre
    try:
        _, eigenvectors = np.linalg.eigh(np.einsum("ab, ac -> bc", centred, centred))
    except (np.linalg.LinAlgError, ValueError):
        return mean_plane2(points)
    return eigenvectors[:, 0], centre


def calc_ellipsoid_matrix(uij_cart: List[float]) -> np.ndarray:
    """Calculate transformation matrix for ellipsoid visualization.

    Parameters
    ----------
    uij_cart : list of float
        Uij values in Cartesian coordinates. Order is U11, U22, U33, U12, U13,
        U23.

    Returns
    -------
    np.ndarray
        3x3 transformation matrix for ellipsoid visualization.

    Notes
    -----
    For conversion from CIF convention, see R. W. Grosse-Kunstleve,
    J. Appl. Cryst. (2002). 35, 477-480.
    """
    uij_mat = np.array(uij_cart)[np.array([[0, 3, 4], [3, 1, 5], [4, 5, 2]])]

    eigenvalues, eigenvectors = np.linalg.eig(uij_mat)
    if np.linalg.det(eigenvectors) != 1:
        eigenvectors /= np.linalg.det(eigenvectors)

    return (eigenvectors @ np.diag(np.sqrt(eigenvalues))).T


def calc_bond_length_rot(position1: np.ndarray, position2: np.ndarray) -> Tuple[np.ndarray, float, np.ndarray]:
    """Calculate cylinder transformation for bond visualization.

    Parameters
    ----------
    position1 : np.ndarray
        3D coordinates of first atom.
    position2 : np.ndarray
        3D coordinates of second atom.

    Returns
    -------
    np.ndarray
        Mean position between atoms.
    float
        Distance between atoms.
    np.ndarray
        Rotation matrix for cylinder transformation.

    Notes
    -----
    Converts a unit length cylinder aligned with y-axis to connect two atomic
    positions.
    """
    mean_position = (position1 + position2) / 2
    length = np.linalg.norm(position1 - position2)
    unit = (position2 - position1) / length
    z = np.array([0.0, 0, 1])
    v = np.cross(unit, z)
    s = np.sqrt(np.sum(v**2))
    c = np.dot(unit, z)
    v_x = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rot = np.identity(3)
    rot[:3, :3] += v_x + v_x @ v_x * (1 - c) / s**2
    return mean_position, length, rot


def get_unique_bonds(structure, disorder_groups: List[str]) -> Tuple[Tuple[int, int], ...]:
    """Get unique bonds considering disorder groups.

    Parameters
    ----------
    structure : object
        Crystal structure object containing scatterers and sites.
    disorder_groups : list of str
        List of disorder group assignments for each atom.

    Returns
    -------
    tuple of tuple
        Pairs of atom indices representing unique bonds.

    Notes
    -----
    Returns bonds where either one atom is not in a disorder group or both
    atoms are in the same disorder group.
    """
    elements = flex.std_string([scatterer.element_symbol() for scatterer in structure.scatterers()])
    bond_set = build_simple_two_way_bond_sets(structure.sites_cart(), elements)
    unique_bonds = set(tuple(sorted([i, j])) for i, bonds in enumerate(bond_set) for j in bonds)
    one_nondisorder = [
        disorder_groups[index1] == "." or disorder_groups[index2] == "." for index1, index2 in unique_bonds
    ]
    same_group = [disorder_groups[index1] == disorder_groups[index2] for index1, index2 in unique_bonds]
    return tuple(indexes for indexes, cond1, cond2 in zip(unique_bonds, one_nondisorder, same_group) if cond1 or cond2)


def create_scene(
    block: cif.model.block,
) -> trimesh.Scene:
    """Create 3D visualization of crystal structure.

    Parameters
    ----------
    block : cif.model.block
        CIF data block containing structure information.

    Returns
    -------
    trimesh.Scene
        3D scene containing structure visualization.

    Notes
    -----
    Creates a scene with atoms as spheres/ellipsoids and bonds as cylinders.
    Atoms are colored by element and bonds are shown in dark gray.
    """
    name = "qcrbox"
    new_model = cif.model.cif()
    new_model[name] = block
    structure = cif.cctbx_data_structures_from_cif(cif_model=new_model).xray_structures[name]

    unit_cell = structure.crystal_symmetry().unit_cell()

    xyz_carts = np.array(structure.sites_cart())
    xyz_carts -= xyz_carts.mean(axis=0)

    scene = trimesh.Scene()

    for xyz_cart, scatterer in zip(xyz_carts, structure.scatterers()):
        uij_cart = scatterer.u_cart_plus_u_iso(unit_cell)
        element_values = element_dict[scatterer.element_symbol()]

        if scatterer.u_star[0] != -1.0:
            ell_rot = calc_ellipsoid_matrix(uij_cart)
            sphere = trimesh.creation.uv_sphere(radius=1)

            # Create a 4x4 transformation matrix
            transform = np.eye(4)
            transform[:3, :3] = ell_rot.T
            transform[:3, 3] = xyz_cart

            sphere.apply_transform(transform)
            sphere.visual.face_colors = trimesh.visual.color.hex_to_rgba(element_values.atom_colour)
            scene.add_geometry(sphere, node_name=scatterer.label)

            ring_color = trimesh.visual.color.hex_to_rgba(element_values.ring_colour)

            # Add ring for anisotropic atoms
            ring = trimesh.creation.annulus(r_min=0.95, r_max=1.05, height=0.1)
            ring.apply_transform(transform)
            ring.visual.face_colors = ring_color
            scene.add_geometry(ring, node_name=f"{scatterer.label}_ring")

            # Ring 2 (XZ plane)
            ring2 = trimesh.creation.annulus(r_min=0.95, r_max=1.05, height=0.1)
            rot_x = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
            ring2.apply_transform(rot_x)
            ring2.apply_transform(transform)
            ring2.visual.face_colors = ring_color
            scene.add_geometry(ring2, node_name=f"{scatterer.label}_ring2")

            # Ring 3 (YZ plane)
            ring3 = trimesh.creation.annulus(r_min=0.95, r_max=1.05, height=0.1)
            rot_y = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
            ring3.apply_transform(rot_y)
            ring3.apply_transform(transform)
            ring3.visual.face_colors = ring_color
            scene.add_geometry(ring3, node_name=f"{scatterer.label}_ring3")

        elif scatterer.element_symbol() == "H":
            sphere = trimesh.creation.icosphere(radius=0.15)
            sphere.apply_translation(xyz_cart)
            sphere.visual.face_colors = trimesh.visual.color.hex_to_rgba(element_values.atom_colour)
            scene.add_geometry(sphere, node_name=scatterer.label)
        else:
            ell_rot = calc_ellipsoid_matrix(uij_cart)
            sphere = trimesh.creation.uv_sphere(radius=np.linalg.norm(ell_rot, axis=1)[0])
            sphere.apply_translation(xyz_cart)
            sphere.visual.face_colors = trimesh.visual.color.hex_to_rgba(element_values.atom_colour)
            scene.add_geometry(sphere, node_name=scatterer.label)

    labels = [scatterer.label for scatterer in structure.scatterers()]

    # if '_geom_bond_site_symmetry_2' in block:
    #    atom_labels1 = list(block['_geom_bond_atom_site_label_1'])
    #    atom_labels2 = list(block['_geom_bond_atom_site_label_2'])
    #    atom_symms = list(block['_geom_bond_site_symmetry_2'])
    #    bonds = [
    #        (labels.index(l1), labels.index(l2)) for l1, l2, symm in zip(atom_labels1, atom_labels2, atom_symms)
    #        if symm == '.'
    #    ]
    # else:
    #    distances = np.linalg.norm(xyz_carts[np.newaxis,:] - xyz_carts[:,np.newaxis], axis=-1)
    #    rads = np.array([element_dict[scatterer.element_symbol()].radius for scatterer in structure.scatterers()])
    #    sums = rads[:, np.newaxis] + rads[np.newaxis, :]
    #    atoms1, atoms2 = np.where(np.logical_and(1.15*sums > distances, distances > 0))
    #    bonds = set([tuple(sorted(val)) for val in zip(atoms1, atoms2)])

    disorder_groups = block.get("_atom_site_disorder_group", ["."] * len(block["_atom_site_fract_x"]))

    bonds = get_unique_bonds(structure, disorder_groups)

    for index1, index2 in bonds:
        mean_position, length, rot = calc_bond_length_rot(xyz_carts[index1], xyz_carts[index2])
        cylinder = trimesh.creation.cylinder(radius=0.04, height=length)
        transform = np.eye(4)
        transform[:3, :3] = rot.T
        transform[:3, 3] = mean_position
        cylinder.apply_transform(transform)
        cylinder.visual.face_colors = [100, 100, 100, 255]  # Dark gray color
        scene.add_geometry(cylinder, node_name=f"bond_{labels[index1]}_{labels[index2]}")

    return scene
