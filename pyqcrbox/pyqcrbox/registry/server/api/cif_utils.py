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
    "first_cif_input_parameter",
    "parse_cif_first_block",
    "check_command_can_run",
    "entry_sets_by_name",
]

CIF_DATA_FILE_DTYPE = "QCrBox.cif_data_file"


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
# the loaded file) are all present in the file's first CIF block. The stored
# parameter dicts have exactly the shape of the application YAML parameter
# sections, so the qcrboxtools YAML helpers are reused directly. Note that
# stored files are in the unified convention (see `to_unified_cif_bytes`),
# which is what makes checking unified entry names against the block sound.


def first_cif_input_parameter(parameters: dict) -> dict | None:
    """Return the first `QCrBox.cif_data_file` parameter dict of a command, if any."""
    for param in parameters.values():
        if isinstance(param, dict) and param.get("dtype") == CIF_DATA_FILE_DTYPE:
            return param
    return None


def entry_sets_by_name(cif_entry_sets: list[dict]) -> dict:
    """Convert an application's stored `cif_entry_sets` list into the mapping
    expected by qcrboxtools' `cif_entries_from_parameter_dict`."""
    return {
        entry_set["name"]: {
            "required": entry_set.get("required") or [],
            "optional": entry_set.get("optional") or [],
        }
        for entry_set in cif_entry_sets
        if isinstance(entry_set, dict) and "name" in entry_set
    }


def parse_cif_first_block(file_contents: bytes):
    """Parse file contents and return the first CIF block, or None if the
    contents are not parseable CIF."""
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


def check_command_can_run(
    parameters: dict, entry_sets: dict, block
) -> tuple[bool, list[str], str | None]:
    """Check whether a command with the given parameter dicts can run on a CIF block.

    Returns `(can_run, missing_entries, reason)`. `block` may be None (file is
    not parseable CIF), in which case commands with a CIF input parameter
    cannot run. Mirrors qcrboxtools' `can_run_command`, but works on the
    registry's stored parameter/entry-set data instead of YAML files.
    """
    cif_param = first_cif_input_parameter(parameters)
    if cif_param is None:
        return True, [], None

    if block is None:
        return False, [], "not a parseable CIF file"

    try:
        from qcrboxtools.cif.cif2cif import (
            NoKeywordsError,
            NonExistentEntrySetError,
            OneOfEntryNotResolvableError,
            YmlCifInputSettings,
            cif_entries_from_parameter_dict,
            yml_entries_resolve_special,
        )
        from qcrboxtools.cif.entries import entry_to_unified_keyword
    except ImportError:
        logger.warning("qcrboxtools is not available; cannot evaluate can-run checks")
        return True, [], "can-run check unavailable"

    try:
        required_entries, optional_entries, custom_categories = cif_entries_from_parameter_dict(
            cif_param, entry_sets
        )
    except NoKeywordsError:
        return True, [], None
    except NonExistentEntrySetError:
        # The application's entry sets are not (yet) stored server-side, e.g.
        # because it has not re-registered since the column was introduced.
        return True, [], "entry sets unresolved - application may need re-registration"

    input_settings = YmlCifInputSettings(
        required_entries, optional_entries, custom_categories, cif_param.get("merge_su", False)
    )
    try:
        resolved = yml_entries_resolve_special(input_settings, block)
    except OneOfEntryNotResolvableError as exc:
        return False, [str(exc)], None

    missing_entries = [
        unified
        for entry in resolved.required_entries
        if (unified := entry_to_unified_keyword(entry, resolved.custom_categories)) not in block
    ]
    return not missing_entries, missing_entries, None
