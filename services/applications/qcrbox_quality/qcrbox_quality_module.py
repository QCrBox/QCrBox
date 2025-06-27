from pathlib import Path
from textwrap import dedent

import numpy as np
import plotly.graph_objects as go
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.resources import INLINE
from iotbx.cif import reader
from qcrboxtools.analyse.ortep import cif2ortep_glb
from qcrboxtools.analyse.quality.cif import from_entry
from qcrboxtools.analyse.quality.html.quality_box import (
    QualityIndicatorBox,
    quality_div_group,
)
from qcrboxtools.cif.cif2cif import cif_file_to_specific_by_yml
from qcrboxtools.cif.read import cifdata_str_or_index, read_cif_safe

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
            value=f'{float(cif_block["_refine_ls.r_factor_all"]) * 100:.2f}',
            unit="%",
            quality_level=from_entry(cif_block, "_refine_ls.r_factor_all"),
        ),
        QualityIndicatorBox(
            name=r"$wR_2(F^2)$",
            value=f'{float(cif_block["_refine_ls.wr_factor_gt"]) * 100:.2f}',
            unit="%",
            quality_level=from_entry(cif_block, "_refine_ls.wr_factor_gt"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{max}$",
            value=cif_block["_refine.diff_density_max"],
            unit=r"$e\,\unicode{x212B}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_max"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{min}$",
            value=cif_block["_refine.diff_density_min"],
            unit=r"$e\,\unicode{x212B}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_min"),
        ),
        QualityIndicatorBox(
            name=r"$d_\mathrm{min}$",
            value=cif_block["_refine_ls.d_res_high"],
            unit=r"$\unicode{x212B}$",
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
        .indicators-container {
            display: flex;
            gap: 16px;
            justify-content: center;
            flex-direction: row;
            padding: 20px;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
        }

        .indicator {
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            width: 100px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 70px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }

        .indicator:hover {
            transform: translateY(-2px);
        }

        /* Data Quality Colour Classes with slightly muted colors */
        .data-quality-good {
            background-color: #2e9d4f;
            color: #ffffff;
        }

        .data-quality-goodish {
            background-color: #7ed957;
            color: #000000;
        }

        .data-quality-marginal {
            background-color: #e4ef4c;
            color: #000000;
        }

        .data-quality-badish {
            background-color: #ffa726;
            color: #000000;
        }

        .data-quality-bad {
            background-color: #f44336;
            color: #ffffff;
        }

        .data-quality-information {
            background-color: #78909c;
            color: #ffffff;
        }

        /* Indicator Content */
        .indicator .name {
            font-size: 14px;
            line-height: 1.4;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 40px;
        }

        .indicator .value {
            font-size: 18px;
            font-weight: 600;
            margin: 4px 0;
        }

        .indicator .unit {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 4px;
            line-height: 1.2;
        }

        /* MathJax specific adjustments */
        .mjx-chtml {
            font-size: 110% !important;
            margin: 0 !important;
        }

        .name .mjx-chtml {
            display: inline-flex !important;
            align-items: center;
        }
    """
    ).strip()
    mathjax = dedent(
        r"""
        <script type="text/javascript" id="MathJax-script" async
        src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
        </script>
    """
    ).strip()

    css_in_html = f"<style>\n{boxes_css}\n</style>\n\n"

    html_snippet = mathjax + css_in_html + quality_div_group(indicators)
    output_html_path.write_text(html_snippet, encoding="UTF-8")
    # output_html_path.with_suffix(".css").write_text(boxes_css, encoding="UTF-8")


def fobs_calc_block_from_cif(input_cif_path: Path, plotting_module: str = "bokeh"):
    work_cif_path = input_cif_path.parent / "qcrbox_work.cif"

    cif_file_to_specific_by_yml(
        input_cif_path,
        work_cif_path,
        YAML_PATH,
        f"fobs_div_fcalc_{plotting_module}",
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

    cif_block = fobs_calc_block_from_cif(input_cif_path, "plotly")

    f_calc_sq = np.array(cif_block["_refln_F_squared_calc"], dtype=np.float64)
    f_obs_sq = np.array(cif_block["_refln_F_squared_meas"], dtype=np.float64)

    fobs = np.zeros_like(f_obs_sq)
    fobs[f_obs_sq > 0] = np.sqrt(f_obs_sq[f_obs_sq > 0])
    fobs[f_obs_sq < 0] = -np.sqrt(np.abs(f_obs_sq[f_obs_sq < 0]))
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

    html_snippet = fig.to_html(include_mathjax="cdn", full_html=False)

    output_html_path.write_text(html_snippet, encoding="UTF-8")


def fobs_div_fcalc_bokeh(input_cif_path, output_html_path):
    input_cif_path = Path(input_cif_path)
    output_html_path = Path(output_html_path)

    cif_block = fobs_calc_block_from_cif(input_cif_path, "bokeh")

    f_calc_sq = np.array(cif_block["_refln_F_squared_calc"], dtype=np.float64)
    f_obs_sq = np.array(cif_block["_refln_F_squared_meas"], dtype=np.float64)
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
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()
    snippet = f"{js_resources}\n{css_resources}\n{plot_script}\n{plot_div}"

    output_html_path.write_text(snippet, encoding="UTF-8")


def ortep_3d(input_cif_path, output_html_path):
    input_cif_path = Path(input_cif_path)
    output_html_path = Path(output_html_path)
    output_glb_path = output_html_path.parent / "structure.glb"
    cif2ortep_glb(input_cif_path, output_glb_path)
    html_snippet = dedent(
        """
        <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js">
        </script>
        <style>
        model-viewer {
            width: 100%;
            height: 100%;
        }
        </style>

        <model-viewer alt="3D ORTEP" src="structure.glb" shadow-intensity="1" camera-controls touch-action="pan-y">
        </model-viewer>
    """
    ).strip()
    output_html_path.write_text(html_snippet, encoding="UTF-8")
