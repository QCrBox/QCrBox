from abc import ABC, abstractmethod
from io import StringIO


class CIFIOAdapter(ABC):
    @abstractmethod
    def __init__(self, cif_text: str):
        pass

    @abstractmethod
    def get_entry_from_cif_block(self, entry_name: str) -> str | int | float | bool:
        pass

    @abstractmethod
    def get_loop_entry_from_cif_block(
        self, entry_name: str, row_lookups: list[tuple[str, str]]
    ) -> str | int | float | bool:
        pass


class ValueMissingError(Exception):
    pass


class PyCIFRWAdapter(CIFIOAdapter):
    def __init__(self, cif_text: str):
        from CifFile import ReadCif

        string_io = StringIO(cif_text)

        cf = ReadCif(string_io)
        block = cf.first_block()
        self.block = block

    def get_entry_from_cif_block(self, entry_name: str) -> str | int | float | bool:
        """
        Get a value from a CIF block using an entry name.

        Args:
            cif_block: The CIF block to extract the value from.
            cif_entry (str): The CIF entry to extract the value from.
        """
        if entry_name not in self.block:
            raise ValueMissingError(f"CIF entry '{entry_name}' not found in CIF block.")

        return self.block[entry_name]

    def get_loop_entry_from_cif_block(
        self, entry_name: str, row_lookups: list[tuple[str, str]]
    ) -> str | int | float | bool:
        """
        Get a value from a CIF block loop using multiple lookup conditions.

        Args:
            entry_name: The CIF entry to extract from the matched row
            row_lookups: List of (column_name, expected_value) tuples for row matching.
                        All conditions must match (AND logic).

        Returns
        -------
            The value from the entry_name column in the first row matching all conditions.

        Raises
        ------
            ValueMissingError: If entry_name or any lookup column doesn't exist
            ValueError: If no row matches all lookup conditions

        """
        # Validate entry exists
        if entry_name not in self.block:
            raise ValueMissingError(f"CIF entry '{entry_name}' not found in CIF block.")

        # Validate all lookup columns exist
        for lookup_name, _ in row_lookups:
            if lookup_name not in self.block:
                raise ValueMissingError(f"CIF entry '{lookup_name}' not found in CIF block.")

        # Get the loop
        loop = self.block.GetLoop(entry_name)


        # Find the indexes matching the lookup conditions
        indexes = [set(idx for idx, val in enumerate(loop[key]) if val == test_val) for key, test_val in row_lookups]

        # get the overlap between the index sets
        overlap = indexes[0].intersection(*indexes[1:])

        if len(overlap) == 1:
            return loop[entry_name][next(iter(overlap))]

        # More than one or none found
        lookup_desc = " AND ".join(f"{name}={val}" for name, val in row_lookups)
        if len(overlap) > 1:
            rows = " ".join(overlap)
            raise ValueError(f"More than one row found matching conditions: {lookup_desc}. Indexes in loop {rows}")
        raise ValueError(f"No row found matching conditions: {lookup_desc}")
