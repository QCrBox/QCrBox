from pathlib import Path
from textwrap import dedent

from qcrboxtools.analyse.quality.cif import from_entry
from qcrboxtools.analyse.quality.html.quality_box import (
    QualityIndicatorBox,
    quality_div_group,
)
from qcrboxtools.cif.read import cifdata_str_or_index

from .util import read_cif_text_as_unified


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
            unit=r"$e\,\mathrm{Ang}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_max"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{min}$",
            value=cif_block["_refine.diff_density_min"],
            unit=r"$e\,\mathrm{Ang}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_min"),
        ),
        QualityIndicatorBox(
            name=r"$d_\mathrm{min}$",
            value=cif_block["_refine_ls.d_res_high"],
            unit=r"$\mathrm{Ang}$",
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

    body_snippet = '<div class="section indicators">\n' + quality_div_group(indicators) + "\n</div>"

    css_template_path = Path(__file__).parents[1] / "templates" / "quality.css"

    css_snippet = css_template_path.read_text(encoding="utf-8").strip()
    return header_snippet, body_snippet, css_snippet
