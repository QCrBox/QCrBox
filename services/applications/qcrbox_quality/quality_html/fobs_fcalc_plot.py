import numpy as np
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.resources import CDN
from django.template.loader import render_to_string
from qcrboxtools.cif.read import cifdata_str_or_index

from .util import read_cif_text_as_unified


def fobs_calc_block_from_cif(cif_text):
    """
    Extract CIF block containing F_obs and F_calc data from CIF text.

    This will either return the first block directly or parse the
    "_iucr.refine_fcf_details" embedded fcf CIF content if present.

    Parameters
    ----------
    cif_text : str
        CIF text content containing crystallographic data.

    Returns
    -------
    dict
        CIF block dictionary containing reflection data.

    """
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    if "_iucr.refine_fcf_details" in cif_block:
        cif_model = read_cif_text_as_unified(cif_block["_iucr.refine_fcf_details"])
        cif_block, _ = cifdata_str_or_index(cif_model, 0)

    return cif_block


def diagonal_line_parameters(fobs, fcalc):
    """
    Calculate parameters for diagonal line to fill the view range in F_obs vs F_calc plot.

    Parameters
    ----------
    fobs : array_like
        Array of observed structure factors.
    fcalc : array_like
        Array of calculated structure factors.

    Returns
    -------
    tuple
        A tuple containing:
        - line_start_end : list of float
            Start and end coordinates for the diagonal line.
        - view_range : list of float
            Range for plot axes [min, max].

    """
    max_f = max((np.max(fobs), np.max(fcalc)))
    min_f = min((np.min(fobs), np.min(fcalc)))
    add_f = 0.05 * (max_f - min_f)
    line_start_end = [min_f - 100 * add_f, max_f + 100 * add_f]
    view_range = [min_f - add_f, max_f + add_f]
    return line_start_end, view_range


def create_hkl_labels(cif_block):
    """
    Create Miller index labels from CIF block reflection data.

    CIF block needs to contain "_refln.index_h", "_refln.index_k", and "_refln.index_l".

    Parameters
    ----------
    cif_block : dict
        CIF block dictionary containing reflection data.

    Returns
    -------
    list of str or None
        List of Miller index labels in format "(h k l)" if Miller indices
        are present in the CIF block, otherwise None.

    """
    miller_entries = [f"_refln.index_{i}" for i in ("h", "k", "l")]
    if all(entry in cif_block for entry in miller_entries):
        miller_content = list(cif_block[entry] for entry in miller_entries)
        return [f"({mil_h} {mil_k} {mil_l})" for mil_h, mil_k, mil_l in zip(*miller_content, strict=False)]
    return None


def fobs_div_fcalc(cif_text):
    """
    Generate interactive F_obs vs F_calc scatter plot from CIF data.

    This function creates a Bokeh scatter plot comparing observed and calculated
    structure factors. The plot includes a diagonal line for reference and
    optional tooltips with Miller indices.

    Parameters
    ----------
    cif_text : str
        CIF text content containing crystallographic reflection data.

    Returns
    -------
    tuple
        A tuple containing:
        - header_snippet : str
            JavaScript resources for the plot.
        - body_snippet : str
            HTML div containing the plot script and div.
        - css_snippet : str
            CSS resources for the plot.

    """
    cif_block = fobs_calc_block_from_cif(cif_text)
    print(cif_block.keys())

    f_calc_sq = np.array(cif_block["_refln.f_squared_calc"], dtype=np.float64)
    f_obs_sq = np.array(cif_block["_refln.f_squared_meas"], dtype=np.float64)
    fobs = np.zeros_like(f_obs_sq)
    fobs[f_obs_sq > 0] = np.sqrt(f_obs_sq[f_obs_sq > 0])
    fobs[f_obs_sq < 0] = -np.sqrt(np.abs(f_obs_sq[f_obs_sq < 0]))
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
        sizing_mode="stretch_both",
    )
    p.scatter("Fobs", "Fcalc", source=source)
    p.line(line_start_end, line_start_end, line_width=1, color="#000000", alpha=0.2)
    plot_script, plot_div = components(p)

    header_snippet = render_to_string(
        "category_components/fobs_fcalc/header.html",
        {
            "bokeh_cdn": CDN.render_js(),
            "plot_script": plot_script,
        },
    )

    body_snippet = render_to_string(
        "category_components/fobs_fcalc/body.html",
        {
            "plot_div": plot_div,
        },
    )
    css_snippet = CDN.render_css()

    return header_snippet, body_snippet, css_snippet
