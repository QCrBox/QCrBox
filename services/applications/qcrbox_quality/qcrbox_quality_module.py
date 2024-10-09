from pathlib import Path

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

    with open(output_html_path, "w", encoding="UTF-8") as fobj:
        fobj.write(quality_div_group(indicators))
