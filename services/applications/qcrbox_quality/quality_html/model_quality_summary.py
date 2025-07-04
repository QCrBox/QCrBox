from django.template.loader import render_to_string
from qcrboxtools.analyse.quality.cif import from_entry
from qcrboxtools.cif.read import cifdata_str_or_index

from .base import QualityIndicatorBox
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
            unit=r"$e\,\mathrm{Å}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_max"),
        ),
        QualityIndicatorBox(
            name=r"$\rho_\mathrm{min}$",
            value=cif_block["_refine.diff_density_min"],
            unit=r"$e\,\mathrm{Å}^{-3}$",
            quality_level=from_entry(cif_block, "_refine.diff_density_min"),
        ),
        QualityIndicatorBox(
            name=r"$d_\mathrm{min}$",
            value=cif_block["_refine_ls.d_res_high"],
            unit=r"$\mathrm{Å}$",
            quality_level=from_entry(cif_block, "_refine_ls.d_res_high"),
        ),
        QualityIndicatorBox(
            name="GooF",
            value=cif_block["_refine_ls.goodness_of_fit_ref"],
            unit="",
            quality_level=from_entry(cif_block, "_refine_ls.goodness_of_fit_ref"),
        ),
    ]

    header_snippet = render_to_string("category_components/model_quality/header.html", {})

    body_snippet = render_to_string(
        "category_components/model_quality/body.html",
        {
            "indicators": indicators,
        },
    )

    css_snippet = render_to_string("category_components/model_quality/style.css", {})
    return header_snippet, body_snippet, css_snippet
