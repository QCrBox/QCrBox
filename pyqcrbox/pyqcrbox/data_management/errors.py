__all__ = [
    "DatasetNotFoundError",
    "CalculationAlreadyExistsError",
]


class DatasetNotFoundError(Exception):
    """Exception was a Dataset was not found."""


class CalculationAlreadyExistsError(Exception):
    """Exception when a calculation with a certain ID already exists."""
