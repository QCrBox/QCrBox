from qcrboxtools.cif.read import read_cif_safe, cifdata_str_or_index
from qcrboxtools.analyse.quality.cif import from_entry
import json
import numpy as np
from collections import namedtuple
from typing import Tuple
from iotbx import cif


def cif_quality2colour(cif_block, cif_entry):
    quality = from_entry(cif_block, cif_entry)
    return "DataQuality." + quality.name

def basic_model_quality_indicators(input_cif_path, output_json_path):
    cif_model = read_cif_safe(input_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    chart_dict = {
        "type": "QualityValueDisplay",
        "data": [
            {
                "name": r"R_1(F)",
                "value": cif_block["_refine_ls.r_factor_all"],
                "unit": "%",
                "colour": cif_quality2colour(cif_block, "_refine_ls.r_factor_all")
            },
            {
                "name": r"$wR_2(F^2)$",
                "value": cif_block["_refine_ls.wr_factor_gt"],
                "unit": "%",
                "colour": cif_quality2colour(cif_block, "_refine_ls.wr_factor_gt")
            },
            {
                "name": r"$\rho_\mathrm{max}$",
                "value": cif_block["_refine.diff_density_max"],
                "unit": r"$e\,\AA^{-3}$",
                "colour": cif_quality2colour(cif_block, "_refine_diff_density_max")
            },
            {
                "name": r"$\rho_\mathrm{min}$",
                "value": cif_block["_refine.diff_density_min"],
                "unit": r"$e\,\AA^{-3}$",
                "colour": cif_quality2colour(cif_block, "_refine_diff_density_min")
            },
            {
                "name": r"$d_\mathrm{min}$",
                "value": cif_block["_refine_ls.d_res_high"],
                "unit": r"$\AA$",
                "colour": cif_quality2colour(cif_block, "_refine_ls.d_res_high")
            },
            {
                "name": r"GooF",
                "value": cif_block["_refine_ls.goodness_of_fit_ref"],
                "unit": "",
                "colour": cif_quality2colour(cif_block, "_refine_ls.goodness_of_fit_ref")
            }
        ],
    }
    # TODO: Use return value if available
    #return json.dumps(chart_dict)

    # For now write to file
    with open(output_json_path, "w") as fobj:
        json.dump(chart_dict, fobj)



