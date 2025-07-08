from django.template.loader import render_to_string
from qcrboxtools.analyse.quality.precision import precision_all_data, precision_all_data_quality
from qcrboxtools.cif.read import cifdata_str_or_index

from .base import QualityIndicatorBox
from .util import read_cif_text_as_unified


class PrecisionQualityIndicatorBox(QualityIndicatorBox):
    """
    Specialized quality indicator box for precision metrics.

    Extends the base QualityIndicatorBox to handle precision-specific
    formatting and display requirements.
    """

    @staticmethod
    def from_precision_data(name: str, value: float, unit: str, quality_level):
        """
        Create a PrecisionQualityIndicatorBox from precision analysis data.

        Parameters
        ----------
        name : str
            The name of the precision indicator.
        value : float
            The calculated precision value.
        unit : str
            The unit of the precision indicator.
        quality_level : DataQuality
            The assessed quality level.

        Returns
        -------
        PrecisionQualityIndicatorBox
            An instance configured for precision display.

        """
        # Format value based on type and magnitude
        if unit == "%":
            formatted_value = f"{value * 100:.2f}"
        elif abs(value) < 0.01:
            formatted_value = f"{value:.4f}"
        elif abs(value) < 1.0:
            formatted_value = f"{value:.3f}"
        else:
            formatted_value = f"{value:.2f}"

        return PrecisionQualityIndicatorBox(name, formatted_value, unit, quality_level)


def precision_quality_indicators(cif_text: str) -> tuple[set[str], set[str], set[str]]:
    """
    Generate HTML and CSS snippets for precision quality indicators from CIF text.

    This function calculates precision indicators using the precision_all_data
    and precision_all_data_quality functions, then prepares the necessary
    HTML and CSS snippets to display them in a structured format.

    Parameters
    ----------
    cif_text : str
        The CIF text content containing crystallographic data.

    Returns
    -------
    tuple
        A tuple containing:
        - A set with the header HTML snippet for MathJax rendering.
        - A set with the body HTML snippet containing precision indicators.
        - A set with the CSS snippet for styling the precision indicators.

    """
    try:
        # Create temporary file from CIF text to work with precision analysis functions
        cif_model = read_cif_text_as_unified(cif_text)
        cif_block, _ = cifdata_str_or_index(cif_model, 0)

        # Define the precision indicators to display with their display names and units
        precision_entries = [
            ("d_min upper", r"$d_{\mathrm{min}}$", r"$\mathrm{Å}$"),
            ("Mean Redundancy", "Redundancy", ""),
            ("R_meas", r"$R_{\mathrm{meas}}$", "%"),
            ("R_pim", r"$R_{\mathrm{pim}}$", "%"),
            ("CC1/2", r"$\mathrm{CC}_{1/2}$", ""),
            ("I/sigma(I)", r"$I/\sigma(I)$", ""),
            ("Completeness", "Completeness", "%"),
        ]

        # Calculate precision indicators
        precision_results = precision_all_data(cif_block, indicators=[entr[0] for entr in precision_entries])
        quality_results = precision_all_data_quality(precision_results)

        indicators = []
        for key, display_name, unit in precision_entries:
            if key in precision_results:
                value = precision_results[key]
                quality_level = quality_results.get(key)
                if quality_level is not None:
                    indicator = PrecisionQualityIndicatorBox.from_precision_data(
                        display_name, value, unit, quality_level
                    )
                    indicators.append(indicator)

        # If no valid indicators, return empty snippets
        if not indicators:
            return set(), "", set()

    except Exception as e:
        # If precision analysis fails, return empty snippets
        print(f"Precision analysis failed: {e}")
        return set(), "", set()

    # Generate HTML components
    header_snippet = render_to_string("shared_components/mathjax_header.html", {})

    body_snippet = render_to_string(
        "category_components/data_precision_summary/body.html",
        {
            "indicators": indicators,
        },
    )

    css_snippet = render_to_string("shared_components/boxes.css", {})

    return {header_snippet}, body_snippet, {css_snippet}
