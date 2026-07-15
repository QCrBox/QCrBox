# SPDX-License-Identifier: MPL-2.0
"""CIF handling at the registry API boundary.

Uploaded files whose content is CIF-structured are converted to QCrBox's
"unified" convention (cif_core dotted keywords + split standard uncertainties)
before storage, and stored CIF files can be checked against the CIF entry
requirements of registered commands ("can run").

All qcrboxtools imports are lazy: qcrboxtools (which needs cctbx) is installed
in the registry server container and the devbox environment, but not in every
environment that imports pyqcrbox (e.g. the plain `qcb` CLI venv).
"""

from loguru import logger

__all__ = [
    "CifConversionError",
    "to_unified_cif_bytes",
    "parse_cif_first_block",
    "check_command_can_run",
    "entry_sets_by_name",
]


class CifConversionError(ValueError):
    """Raised when uploaded content looks like CIF but cannot be parsed/converted."""


def to_unified_cif_bytes(file_contents: bytes, filename: str) -> bytes:
    """Convert uploaded CIF content to the unified convention.

    Content that does not sniff as CIF (binary data, or text whose first
    non-comment line is not a ``data_`` block header) is returned unchanged —
    this makes the function safe to call on every upload, whatever the file
    extension (`.cif`, `.fcf` and vendor dialects are all converted).

    Raises `CifConversionError` for content that sniffs as CIF but fails to
    parse or convert: such files are rejected at upload rather than stored in
    an unknown state.
    """
    try:
        from qcrboxtools.cif.cif2cif import bytes_to_unified_if_cif
    except ImportError:
        logger.warning(
            f"qcrboxtools is not available; storing {filename!r} without unified-CIF conversion"
        )
        return file_contents

    try:
        return bytes_to_unified_if_cif(file_contents)
    # qcrboxtools/cctbx raise a zoo of exceptions for broken CIFs (including
    # libtbx's `Sorry`, which is a plain Exception subclass); treat them all
    # as "this claims to be CIF but is not parseable".
    except Exception as exc:
        raise CifConversionError(
            f"File {filename!r} looks like a CIF file but could not be parsed/converted "
            f"to the unified convention: {exc}"
        ) from exc


# --- "Can run" checks --------------------------------------------------------
#
# A command can run on a stored data file when the CIF entries required by its
# first `QCrBox.cif_data_file` parameter (the one the frontend auto-fills with
# the loaded file) are all present in the file's first CIF block. The check
# itself lives in `pyqcrbox.cif_entries` (shared with the client-side CIF
# conversion); the stored parameter dicts have exactly the shape it expects.
# Note that stored files are in the unified convention (see
# `to_unified_cif_bytes`), which is what makes checking unified entry names
# against the block sound.

from pyqcrbox.cif_entries import check_command_can_run, entry_sets_by_name  # noqa: E402,F401


def parse_cif_first_block(file_contents: bytes):
    """Parse file contents and return the first CIF block.

    Returns None if the contents are not parseable CIF.
    """
    try:
        from iotbx import cif
        from qcrboxtools.cif.read import cifdata_str_or_index
    except ImportError:
        return None

    try:
        cif_text = file_contents.decode("utf-8")
        model = cif.reader(input_string=cif_text).model()
        block, _ = cifdata_str_or_index(model, "0")
    except BaseException:  # noqa: B036 - cctbx raises BaseException subclasses
        return None
    if block is None or len(block) == 0:
        return None
    return block
