import base64

from django.template.loader import render_to_string
from qcrboxtools.cif.read import cifdata_str_or_index

from .util import read_cif_text_as_unified


def check_ortep_entries_present(cif_block):
    """
    Check if the CIF block contains necessary entries for ORTEP 3D visualization.

    Parameters
    ----------
    cif_block : dict
        CIF block dictionary containing crystallographic data.

    Returns
    -------
    bool
        True if all necessary entries for ORTEP are present, False otherwise.

    """
    required_entries = [
        "_space_group.crystal_system",
        "_space_group_symop.operation_xyz",
        "_cell.length_a",
        "_cell.length_b",
        "_cell.length_c",
        "_cell.angle_alpha",
        "_cell.angle_beta",
        "_cell.angle_gamma",
        "_atom_site.label",
        "_atom_site.type_symbol",
        "_atom_site.fract_x",
        "_atom_site.fract_y",
        "_atom_site.fract_z",
        "_atom_site.U_iso_or_equiv",
        "_atom_site.adp_type",
    ]
    return all(entry in cif_block for entry in required_entries)


def ortep_cifvis_3d(cif_text: str) -> tuple[set[str], str, set[str]]:
    """
    Generate HTML and CSS snippets for displaying a CIF file in a 3D visualization using ORTEP.

    This function encodes the CIF text in base64 and prepares the necessary HTML and CSS
    snippets to render a 3D visualization widget. The widget is styled with a CSS file
    located in the templates directory.

    Parameters
    ----------
    cif_text : str
        The CIF text content to be visualized.

    Returns
    -------
    tuple
        A tuple containing:
        - header_snippet : set[str]
            HTML snippet for the header section, including JavaScript resources.
        - body_snippet : str
            HTML snippet for the body section, containing the 3D visualization widget.
        - css_snippet : set[str]
            CSS snippet for styling the 3D visualization widget.

    """
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)
    if not check_ortep_entries_present(cif_block):
        return {}, "", {}
    cif_b64 = base64.b64encode(cif_text.encode()).decode()

    header_snippet = render_to_string("category_components/ortep/header.html", {})
    html_snippet = render_to_string(
        "category_components/ortep/body.html",
        {
            "cif_b64": cif_b64,
        },
    )
    css_snippet = render_to_string("category_components/ortep/style.css", {})

    return {header_snippet}, html_snippet, {css_snippet}
