import json

import numpy as np
from qcrbox.registry.client import ExternalCommand, QCrBoxRegistryClient
from qcrboxtools.cif.read import read_cif_safe, cifdata_str_or_index

client = QCrBoxRegistryClient()
application = client.register_application(
    "Data Quality",
    version="0.0.1",
)

def dummy_refinement_quality_display(input_cif_path):
    cif_model = read_cif_safe(input_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    chart_dict = {
        "type": "QualityValueDisplay",
        "data": [
            {
                "name": r"R_1(F)",
                "value": cif_block["_refine_ls.r_factor_all"],
                "unit": "%",
                "colour": "DataQuality.GOOD"
            },
            {
                "name": r"$wR_2(F^2)$",
                "value": cif_block["_refine_ls.wr_factor_gt"],
                "unit": "%",
                "colour": "DataQuality.MARGINAL"
            },
            {
                "name": r"$\rho_\mathrm{max}$",
                "value": cif_block["_refine_diff_density_max"],
                "unit": r"$e\,\AA^{-3}$",
                "colour": "DataQuality.BAD"
            },
            {
                "name": r"$\rho_\mathrm{min}$",
                "value": cif_block["_refine_diff_density_min"],
                "unit": r"$e\,\AA^{-3}$",
                "colour": "DataQuality.BAD"
            },
            {
                "name": r"$d_\mathrm{min}$",
                "value": cif_block["_refine_ls.d_res_high"],
                "unit": r"$\AA$",
                "colour": "DataQuality.GOOD"
            },
            {
                "name": r"GooF",
                "value": cif_block["_refine_ls.goodness_of_fit_ref"],
                "colour": "DataQuality.MARGINAL"
            }
        ],
    }

    return json.dumps(chart_dict)

def diederichs_2d_plot(input_cif_path):
    cif_model = read_cif_safe(input_cif_path)
    cif_block, _ = cifdata_str_or_index(cif_model, 0)

    log10i = np.log10(cif_block["_diffrn_refln.intensity_net"])
    i_over_sigma = cif_block["_diffrn_refln.intensity_net"] / cif_block["_diffrn_refln.intensity_net_su"]

    chart_dict = {
        "type": "2DChart",
        "xAxis": {
            "label": r"$\log_{10}(I)$"
        },
        "yAxis": {
            "label": r"$\frac{I}{\sigma(I)}$"
        },
        "charts": [
            {
                "type": "scatter",
                "x": list(log10i),
                "y": list(i_over_sigma),
                "colour": "Content.MAIN"
            }
        ],
        "source_doi": "10.1107/S0907444910014836"
    }

    return json.dumps(chart_dict)


application.register_python_callable(
    "dummy_refinement_quality_display", dummy_refinement_quality_display
)

client.run()
