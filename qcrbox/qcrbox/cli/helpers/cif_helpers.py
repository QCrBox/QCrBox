import re
from pathlib import Path
from typing import List, Union


def list_cif_items(cif_path: Union[str, Path]) -> List[str]:
    """
    Extract and return a list of CIF (Crystallographic Information File) item
    names from a given CIF file.

    Parameters
    ----------
    cif_path : Union[str, Path]
        The path to the CIF file from which to extract item names.

    Returns
    -------
    List[str]
        A list containing the names of CIF items found in the file.

    """
    cif_content = Path(cif_path).read_text()
    # Remove multiline strings that are denoted between two semicolons
    cif_content = '\n'.join(cif_content.split('\n;')[::2])

    return re.findall(r'\n\s*(\_[A-Za-z\.\_\-/0-9]+)', cif_content)
