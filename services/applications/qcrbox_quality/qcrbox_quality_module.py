import base64
from pathlib import Path
from textwrap import dedent

import numpy as np
from bokeh.embed import components
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.resources import INLINE
from iotbx.cif import reader
from qcrboxtools.analyse.quality.cif import from_entry
from qcrboxtools.analyse.quality.html.quality_box import (
    QualityIndicatorBox,
    quality_div_group,
)
from qcrboxtools.cif.entries import cif_to_unified_keywords
from qcrboxtools.cif.read import cifdata_str_or_index
from qcrboxtools.cif.uncertainties import split_su_cif


def read_cif_text_as_unified(input_cif_text):
    """Read a CIF text string and return a unified CIF model."""
    cif_model = reader(input_string=input_cif_text).model()
    cif_model = cif_to_unified_keywords(cif_model)
    cif_model = split_su_cif(cif_model)
    return cif_model


def basic_model_quality_indicators(cif_text):
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)
    cif_block.add_data_item("_refine.diff_density_max", cif_block["_refine_diff.density_max"])
    cif_block.add_data_item("_refine.diff_density_min", cif_block["_refine_diff.density_min"])

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

    header_snippet = dedent(
        r"""
        <script type="text/javascript" id="MathJax-script" async
        src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
        </script>
    """
    ).strip()
    body_snippet = quality_div_group(indicators)

    css_template_path = Path(__file__).parent / "templates" / "quality.css"

    css_snippet = css_template_path.read_text(encoding="utf-8").strip()
    return header_snippet, body_snippet, css_snippet


def fobs_calc_block_from_cif(cif_text):
    cif_model = read_cif_text_as_unified(cif_text)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    if "_iucr.refine_fcf_details" in cif_block:
        cif_model = read_cif_text_as_unified(cif_block["_iucr.refine_fcf_details"])
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
    miller_entries = [f"_refln.index_{i}" for i in ("h", "k", "l")]
    if all(entry in cif_block for entry in miller_entries):
        miller_content = list(cif_block[entry] for entry in miller_entries)
        return [f"({mil_h} {mil_k} {mil_l})" for mil_h, mil_k, mil_l in zip(*miller_content, strict=False)]
    return None


def fobs_div_fcalc_bokeh(input_cif_path):
    input_cif_path = Path(input_cif_path)

    cif_block = fobs_calc_block_from_cif(input_cif_path, "bokeh")

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
    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    header_snippet = js_resources
    body_snippet = plot_script + "\n" + plot_div
    css_snippet = css_resources

    return header_snippet, body_snippet, css_snippet


def ortep_cifvis_3d(cif_model):
    ciftext = str(cif_model)

    with open("cifvis.alldeps.umd.cjs") as fobj:
        js_code = fobj.read()

    cif_b64 = base64.b64encode(ciftext.encode()).decode()

    fragment = dedent(
        f"""
    <div class="cifvis-container" style="width: 100%; height: 100%;">
                
        <cifview-widget 
            id="cifview"
            caption="Crystal Structure"
            style="width: 100%; height: 100%;">
        </cifview-widget>

        <script type="module">            
            // Load the bundle
            {js_code}
            
            // Initialize with CIF data
            const widget = document.getElementById('cifview');
            
            // Wait for custom element to be defined and connected
            customElements.whenDefined('cifview-widget').then(() => {{
                const cifData = atob("{cif_b64}");
                widget.loadFromString(cifData);
            }});
        </script>
    </div>
    """
    )

    return fragment


def prepare__interactive(input_file):
    output_html_folder = Path(".") / "html"
    output_html_folder.mkdir(exist_ok=True)
    input_file = Path(input_file)

    basic_model_snippet = basic_model_quality_indicators(input_file)
    fobs_fcalc_snippet = fobs_div_fcalc_bokeh(input_file)
    ortep_snippet = ortep_cifvis_3d(input_file)

    html_template = dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Crystal Structure Visualization</title>
            
            <style>
                body {{
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}

                .outer-container {{
                    width: 1000px;
                    margin: 0 auto;
                    display: flex;
                    flex-direction: column;
                    gap: 24px;
                }}
                
                .section {{
                    width: 100%;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 24px;
                    background-color: #fff;
                    box-sizing: border-box;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}

                /* Indicators section */
                .section.indicators {{
                    height: 150px; /* Reduced height for metrics display */
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}

                /* Plot section */
                .section.plot {{
                    height: 400px; /* Increased height for better plot visibility */
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}

                /* ORTEP section */
                .section.ortep {{
                    height: 800px; /* Increased height for 3D model */
                }}
                
                .loading {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100%;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    color: #666;
                    font-family: system-ui, -apple-system, sans-serif;
                }}
                
                model-viewer {{
                    width: 100%;
                    height: 100%;
                }}
            </style>

        </head>
        <body>
            <div class="outer-container">
                <!-- Basic Model Quality Indicators Section -->
                <div class="section indicators"
                    {basic_model_snippet}
                </div>
                
                <!-- Fo-Fc Bokeh Plot Section -->
                <div class="section plot"
                    {fobs_fcalc_snippet}
                </div>
                
                <!-- ORTEP Section -->
                <div class="section ortep"
                    {ortep_snippet}
                </div>
            </div>
        </body>
        </html>
    """
    ).strip()

    print(html_template)
