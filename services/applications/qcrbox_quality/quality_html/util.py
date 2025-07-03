from iotbx.cif import reader
from qcrboxtools.cif.entries import cif_to_unified_keywords
from qcrboxtools.cif.uncertainties import split_su_cif


def read_cif_text_as_unified(input_cif_text):
    """Read a CIF text string and return a unified CIF model."""
    cif_model = reader(input_string=input_cif_text).model()
    cif_model = cif_to_unified_keywords(cif_model, custom_categories=["iucr", "olex2"])
    cif_model = split_su_cif(cif_model)
    return cif_model
