from dataclasses import dataclass

from qcrboxtools.analyse.quality.base import DataQuality


@dataclass
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

    name: str
    value: str
    unit: str
    quality_level: DataQuality

    @property
    def css_class(self):
        """
        Returns the CSS class name corresponding to the quality level.

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
