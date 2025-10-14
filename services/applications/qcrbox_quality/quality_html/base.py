from qcrboxtools.analyse.quality.base import DataQuality
from qcrboxtools.analyse.quality.cif import from_entry


class QualityIndicatorBox:
    """
    Represents a data quality indicator box with attributes for display.

    Attributes
    ----------
    name : str
        The name of the data quality indicator.
    value : str
        The value associated with the data quality indicator.
    unit : str
        The unit of the indicator's value (e.g., %, ms).
    quality_level : DataQuality
        The quality level, represented as a `DataQuality` enum.

    """

    def __init__(self, name: str, value: str, unit: str, quality_level: DataQuality):
        """
        Initialize a QualityIndicatorBox instance.

        Parameters
        ----------
        name : str
            The name of the data quality indicator.
        value : str
            The value associated with the data quality indicator.
        unit : str
            The unit of the indicator's value (e.g., %, ms).
        quality_level : DataQuality
            The quality level, represented as a `DataQuality` enum.

        """
        self.name = name
        self.value = value
        self.unit = unit
        self.quality_level = quality_level

    @property
    def css_class(self):
        """
        Return the CSS class name corresponding to the quality level.

        This is used for styling the indicator box based on its quality level.
        """
        data_quality_to_css_name = {
            DataQuality.BAD: "data-quality-bad",
            DataQuality.BADISH: "data-quality-badish",
            DataQuality.MARGINAL: "data-quality-marginal",
            DataQuality.GOODISH: "data-quality-goodish",
            DataQuality.GOOD: "data-quality-good",
            DataQuality.INFORMATION: "data-quality-information",
        }
        return data_quality_to_css_name[self.quality_level]

    @staticmethod
    def from_cif_block(cif_block, entry, name, unit):
        """
        Create a QualityIndicatorBox from a CIF block entry.

        Parameters
        ----------
        cif_block : dict
            The CIF block containing the data.
        entry : str
            The CIF entry key to retrieve the value.
        name : str
            The name of the quality indicator.
        unit : str
            The unit of the quality indicator.

        Returns
        -------
        QualityIndicatorBox
            An instance of QualityIndicatorBox with the specified attributes.

        """
        read_value = cif_block.get(entry, "N/A")
        if read_value in ("N/A", "?"):
            value = "N/A"
            quality_level = DataQuality.INFORMATION
        elif unit == "%":
            value = f"{float(read_value) * 100:.2f}"
            quality_level = from_entry(cif_block, entry)
        else:
            value = f"{float(read_value):.2f}"
            quality_level = from_entry(cif_block, entry)

        return QualityIndicatorBox(name, value, unit, quality_level)
