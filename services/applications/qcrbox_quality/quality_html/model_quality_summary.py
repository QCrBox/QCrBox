from django.template.loader import render_to_string
from qcrboxtools.cif.read import cifdata_str_or_index

from .base import QualityIndicatorBox
from .util import read_cif_text_as_unified


def basic_model_quality_indicators(cif_text):
    """
    Generate HTML and CSS snippets for basic model quality indicators from CIF text.

    This function extracts key quality indicators from the CIF data and prepares
    the necessary HTML and CSS snippets to display them in a structured format.
    Missing indicators are marked as "N/A" with a quality level of INFORMATION.

    Parameters
    ----------
    cif_text : str
        The CIF text content containing crystallographic data.

    Returns
    -------
    tuple
        A tuple containing:
        - header_snippet : str
            HTML snippet for the header section containing JavaScript resources.
        - body_snippet : str
            HTML snippet for the body section containing quality indicators.
        - css_snippet : str
            CSS snippet for styling the quality indicators.

    """
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)
    if "_refine_diff.density_max" in cif_block:
        cif_block.add_data_item("_refine.diff_density_max", cif_block["_refine_diff.density_max"])
    if "_refine_diff.density_min" in cif_block:
        cif_block.add_data_item("_refine.diff_density_min", cif_block["_refine_diff.density_min"])

    entries = [
        ["_refine_ls.r_factor_all", r"$R_1(F)$", "%"],
        ["_refine_ls.wr_factor_gt", r"$wR_2(F^2)$", "%"],
        ["_refine.diff_density_max", r"$\rho_\mathrm{max}$", r"$e\,\mathrm{Å}^{-3}$"],
        ["_refine.diff_density_min", r"$\rho_\mathrm{min}$", r"$e\,\mathrm{Å}^{-3}$"],
        ["_refine_ls.d_res_high", r"$d_\mathrm{min}$", r"$\mathrm{Å}$"],
        ["_refine_ls.goodness_of_fit_ref", "GooF", ""],
    ]

    indicators = [QualityIndicatorBox.from_cif_block(cif_block, entry, name, unit) for entry, name, unit in entries]

    if all(indicator.value == "N/A" for indicator in indicators):
        # If all indicators are "N/A", return empty snippets
        return "", "", ""

    header_snippet = render_to_string("category_components/model_quality/header.html", {})

    body_snippet = render_to_string(
        "category_components/model_quality/body.html",
        {
            "indicators": indicators,
        },
    )

    css_snippet = render_to_string("category_components/model_quality/style.css", {})
    return header_snippet, body_snippet, css_snippet
