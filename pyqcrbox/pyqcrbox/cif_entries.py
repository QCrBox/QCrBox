# SPDX-License-Identifier: MPL-2.0
"""CIF entry resolution and CIF-to-CIF conversion driven by QCrBox spec models.

Historically this logic lived in QCrBoxTools' ``cif2cif/yaml.py`` and worked on
re-parsed application YAML files. QCrBox owns the parsed spec models, so the
spec-to-entry resolution lives here and only the pure CIF operations (reading,
trimming, merging, SU splitting, keyword conversion) are delegated to
qcrboxtools.

All qcrboxtools/iotbx imports are lazy: qcrboxtools (which needs cctbx) is
installed in the application/registry containers but not in every environment
that imports pyqcrbox (e.g. the plain `qcb` CLI venv).

Entry lists may contain plain entry names (``str``) or one-of specifications
(``{"one_of": [...]}``), which are resolved against a concrete CIF block.
"""

from pathlib import Path
from typing import Any

from pyqcrbox.logging import logger
from pyqcrbox.sql_models.base import QCrBoxPydanticBaseModel

__all__ = [
    "NoEntriesDeclaredError",
    "UnknownEntrySetError",
    "OneOfEntryUnresolvableError",
    "CifInputSettings",
    "CifOutputSettings",
    "entry_sets_by_name",
    "input_settings_from_spec",
    "output_settings_from_spec",
    "cif_text_to_specific",
    "cif_file_to_specific",
    "cif_text_merge_to_unified",
    "cif_file_merge_to_unified",
    "check_command_can_run",
]


class NoEntriesDeclaredError(Exception):
    """Raised when a parameter/output spec declares no CIF entries at all."""


class UnknownEntrySetError(Exception):
    """Raised when a spec references a CIF entry set which is not defined."""


class OneOfEntryUnresolvableError(Exception):
    """Raised when none of the alternatives of a one_of entry are present in a block."""


class CifInputSettings(QCrBoxPydanticBaseModel):
    """Resolved CIF entry requirements of an input CIF parameter."""

    required_entries: list[Any] = []
    optional_entries: list[Any] = []
    custom_categories: list[str] = []
    merge_su: bool = False


class CifOutputSettings(QCrBoxPydanticBaseModel):
    """Resolved CIF entry requirements of an output CIF specification."""

    required_entries: list[Any] = []
    optional_entries: list[Any] = []
    invalidated_entries: list[str] = []
    custom_categories: list[str] = []
    select_block: str = "0"


def _normalize_entries(entries: list) -> list:
    """Normalize entry lists to plain strings and {'one_of': [...]} dicts."""
    normalized = []
    for entry in entries or []:
        if isinstance(entry, str | dict):
            normalized.append(entry)
        elif hasattr(entry, "one_of"):  # OneOfCifEntrySpec
            normalized.append({"one_of": list(entry.one_of)})
        else:
            raise ValueError(f"Unsupported CIF entry specification: {entry!r}")
    return normalized


def entry_sets_by_name(cif_entry_sets: list) -> dict:
    """Convert an application's `cif_entry_sets` into a name-indexed mapping.

    Accepts pydantic models or plain dicts; values are dicts with
    required/optional entry lists.
    """
    result = {}
    for entry_set in cif_entry_sets or []:
        if not isinstance(entry_set, dict):
            entry_set = entry_set.model_dump()
        if "name" not in entry_set:
            continue
        result[entry_set["name"]] = {
            "required": _normalize_entries(entry_set.get("required") or []),
            "optional": _normalize_entries(entry_set.get("optional") or []),
        }
    return result


def _expand_entry_sets(entry_set_names: list[str], entry_sets: dict) -> tuple[list, list]:
    """Expand named entry sets into (required, optional) entry lists."""
    required = []
    optional = []
    for name in entry_set_names or []:
        if name not in entry_sets:
            raise UnknownEntrySetError(f"CIF entry set {name!r} is not defined by the application")
        required += entry_sets[name].get("required", [])
        optional += entry_sets[name].get("optional", [])
    return required, optional


def _as_spec_dict(spec) -> dict:
    """Accept parameter/output specs as pydantic models or plain dicts."""
    if isinstance(spec, dict):
        return spec
    return spec.model_dump()


def _entries_from_spec_dict(spec: dict, entry_sets: dict) -> tuple[list, list, list]:
    """Extract (required, optional, custom_categories) from a spec dict.

    Mirrors qcrboxtools' `cif_entries_from_parameter_dict`: entries from named
    sets are expanded, required entries of *optional* sets are demoted to
    optional, and duplicates are removed. Raises `NoEntriesDeclaredError` when
    the spec declares no entries at all (callers use this to skip conversion).
    """
    required = _normalize_entries(spec.get("required_entries") or [])
    optional = _normalize_entries(spec.get("optional_entries") or [])
    required_from_sets, optional_from_sets = _expand_entry_sets(spec.get("required_entry_sets") or [], entry_sets)
    required += required_from_sets
    optional += optional_from_sets

    # for optional entry sets, required entries are optional as well
    opt_required, opt_optional = _expand_entry_sets(spec.get("optional_entry_sets") or [], entry_sets)
    optional += opt_required + opt_optional

    if not required and not optional:
        raise NoEntriesDeclaredError("No entries defining optional or necessary keywords found.")

    def _dedup(entries):
        seen = []
        for entry in entries:
            if entry not in seen:
                seen.append(entry)
        return seen

    required = _dedup(required)
    optional = [entry for entry in _dedup(optional) if entry not in required]
    custom_categories = sorted(set(spec.get("custom_categories") or []))

    return required, optional, custom_categories


def input_settings_from_spec(param_spec, entry_sets: dict) -> CifInputSettings:
    """Resolve the CIF entry requirements of a `QCrBox.cif_data_file` parameter spec."""
    spec = _as_spec_dict(param_spec)
    required, optional, custom_categories = _entries_from_spec_dict(spec, entry_sets)
    return CifInputSettings(
        required_entries=required,
        optional_entries=optional,
        custom_categories=custom_categories,
        merge_su=bool(spec.get("merge_su", False)),
    )


def output_settings_from_spec(output_spec, entry_sets: dict) -> CifOutputSettings:
    """Resolve the CIF entry requirements of a `QCrBox.output_cif` output spec.

    Also accepts an input *parameter* spec: commands without an output CIF
    spec fall back to merging with the input parameter's entries (no
    invalidated entries, first block).
    """
    spec = _as_spec_dict(output_spec)
    required, optional, custom_categories = _entries_from_spec_dict(spec, entry_sets)
    invalidated = list(spec.get("invalidated_entries") or [])
    return CifOutputSettings(
        required_entries=required,
        optional_entries=optional,
        invalidated_entries=sorted(set(invalidated)),
        custom_categories=custom_categories,
        select_block=str(spec.get("output_block", 0)),
    )


def _resolve_entries_against_block(entries: list, block, custom_categories: list[str]) -> list[str]:
    """Resolve one_of alternatives against a CIF block (lazy qcrboxtools)."""
    from qcrboxtools.cif.cif2cif import OneOfEntryNotResolvableError, resolve_special_entries

    try:
        return resolve_special_entries(entries, block, custom_categories)
    except OneOfEntryNotResolvableError as exc:
        raise OneOfEntryUnresolvableError(str(exc)) from exc


def cif_text_to_specific(input_cif_text: str, settings: CifInputSettings) -> str:
    """Convert (unified) CIF text to the entry selection of an input parameter.

    Replicates qcrboxtools' `cif_text_to_specific_by_yml` algorithm with the
    entry settings coming from spec models: the model is unified and SUs are
    split, one_of entries are resolved against the (unified) first block, and
    the model is reduced to the resolved entry selection.
    """
    from iotbx import cif
    from qcrboxtools.cif.cif2cif.base import cif_model_to_specific
    from qcrboxtools.cif.cif2cif.yaml import YmlCifInputSettings, yml_entries_resolve_special
    from qcrboxtools.cif.entries import block_to_unified_keywords, cif_to_unified_keywords
    from qcrboxtools.cif.read import cifdata_str_or_index
    from qcrboxtools.cif.uncertainties import split_su_block, split_su_cif

    qcrboxtools_settings = YmlCifInputSettings(
        settings.required_entries,
        settings.optional_entries,
        settings.custom_categories,
        settings.merge_su,
    )

    cif_model = cif.reader(input_string=input_cif_text).model()
    cif_model = cif_to_unified_keywords(cif_model, qcrboxtools_settings.custom_categories)
    cif_model = split_su_cif(cif_model)
    block, _ = cifdata_str_or_index(cif_model, 0)
    block = block_to_unified_keywords(block, qcrboxtools_settings.custom_categories)
    block = split_su_block(block)

    qcrboxtools_settings = yml_entries_resolve_special(qcrboxtools_settings, block)

    specific_cif_model = cif_model_to_specific(
        cif_model,
        qcrboxtools_settings.required_entries,
        qcrboxtools_settings.optional_entries,
        qcrboxtools_settings.custom_categories,
        qcrboxtools_settings.merge_su,
    )

    return str(specific_cif_model)


def cif_file_to_specific(input_cif_path: str | Path, output_cif_path: str | Path, settings: CifInputSettings) -> None:
    """File-level wrapper around `cif_text_to_specific` (commands consume files)."""
    input_cif_text = Path(input_cif_path).read_text(encoding="UTF-8")
    Path(output_cif_path).write_text(cif_text_to_specific(input_cif_text, settings), encoding="UTF-8")


def cif_text_merge_to_unified(
    input_cif_text: str,
    merge_cif_text: str | None,
    settings: CifOutputSettings,
) -> str:
    """Merge a command's output CIF text back into a pre-existing (unified) CIF.

    Replicates qcrboxtools' `cif_text_merge_to_unified_by_yml` algorithm, with
    the entry settings coming from spec models instead of a re-parsed YAML
    file: the output block is trimmed to the declared entries, converted to
    unified keywords with split SUs, invalidated entries are removed from the
    merge target, and the two blocks are merged.
    """
    from iotbx import cif
    from qcrboxtools.cif.cif2cif import yml_entries_resolve_special
    from qcrboxtools.cif.cif2cif.yaml import YmlCifOutputSettings
    from qcrboxtools.cif.entries import block_to_unified_keywords, entry_to_unified_keyword
    from qcrboxtools.cif.merge import merge_cif_blocks
    from qcrboxtools.cif.read import cifdata_str_or_index
    from qcrboxtools.cif.trim import trim_cif_block
    from qcrboxtools.cif.uncertainties import split_su_block

    qcrboxtools_settings = YmlCifOutputSettings(
        settings.required_entries,
        settings.optional_entries,
        settings.invalidated_entries,
        settings.custom_categories,
        settings.select_block,
    )

    input_cif = cif.reader(input_string=input_cif_text).model()
    # dataset name will be overwritten if merge_cif is not None
    input_block, dataset_name = cifdata_str_or_index(input_cif, qcrboxtools_settings.select_block)
    if merge_cif_text is None:
        merge_block = cif.model.block()
    else:
        # QCrBox cif files have only one block
        merge_block, dataset_name = cifdata_str_or_index(cif.reader(input_string=merge_cif_text).model(), 0)

    qcrboxtools_settings = yml_entries_resolve_special(qcrboxtools_settings, input_block)

    # Cut down the input block to the required entries and convert to unified keywords
    all_entries = qcrboxtools_settings.required_entries + qcrboxtools_settings.optional_entries
    new_input_block = trim_cif_block(
        input_block, keep_only_regexes=all_entries, delete_regexes=[], delete_empty_entries=True
    )

    missing_entries = set(qcrboxtools_settings.required_entries) - set(new_input_block.keys())
    if len(missing_entries) > 0:
        raise ValueError(f"Required entries missing in loaded CIF file: {missing_entries}")

    unified_input_block = block_to_unified_keywords(new_input_block, qcrboxtools_settings.custom_categories)
    unified_input_block = split_su_block(unified_input_block)

    unified_invalidated = [
        entry_to_unified_keyword(entry, qcrboxtools_settings.custom_categories)
        for entry in qcrboxtools_settings.invalidated_entries
    ]

    # Cut down the merge block to the required entries.
    trimmed_merge_block = trim_cif_block(
        merge_block, keep_only_regexes=[], delete_regexes=unified_invalidated, delete_empty_entries=False
    )

    output_cif_block = merge_cif_blocks(trimmed_merge_block, unified_input_block)

    output_cif = cif.model.cif()
    output_cif[dataset_name] = output_cif_block

    return str(output_cif)


def cif_file_merge_to_unified(
    input_cif_path: str | Path,
    output_cif_path: str | Path,
    merge_cif_text: str | None,
    settings: CifOutputSettings,
) -> None:
    """File-level wrapper around `cif_text_merge_to_unified`.

    The input (the command's output CIF) and the merged result are files in
    the calculation work directory; the merge source is passed as text (it
    comes straight from the data manager, no disk round trip needed).
    """
    input_cif_text = Path(input_cif_path).read_text(encoding="UTF-8")
    merged = cif_text_merge_to_unified(input_cif_text, merge_cif_text, settings)
    Path(output_cif_path).write_text(merged, encoding="UTF-8")


def check_command_can_run(parameters: dict, entry_sets: dict, block) -> tuple[bool, list[str], str | None]:
    """Check whether a command with the given parameter dicts can run on a CIF block.

    Returns `(can_run, missing_entries, reason)`. `block` may be None (file is
    not parseable CIF), in which case commands with a CIF input parameter
    cannot run. The check is evaluated against the command's FIRST
    `QCrBox.cif_data_file` parameter (the one the frontend auto-fills with the
    loaded file).
    """
    cif_param = next(
        (
            param
            for param in parameters.values()
            if isinstance(param, dict) and param.get("dtype") == "QCrBox.cif_data_file"
        ),
        None,
    )
    if cif_param is None:
        return True, [], None

    if block is None:
        return False, [], "not a parseable CIF file"

    try:
        settings = input_settings_from_spec(cif_param, entry_sets)
    except NoEntriesDeclaredError:
        return True, [], None
    except UnknownEntrySetError:
        # The application's entry sets are not (yet) stored server-side, e.g.
        # because it has not re-registered since the column was introduced.
        return True, [], "entry sets unresolved - application may need re-registration"

    try:
        from qcrboxtools.cif.entries import entry_to_unified_keyword
    except ImportError:
        logger.warning("qcrboxtools is not available; cannot evaluate can-run checks")
        return True, [], "can-run check unavailable"

    try:
        resolved_required = _resolve_entries_against_block(
            settings.required_entries, block, settings.custom_categories
        )
    except OneOfEntryUnresolvableError as exc:
        return False, [str(exc)], None

    missing_entries = [
        unified
        for entry in resolved_required
        if (unified := entry_to_unified_keyword(entry, settings.custom_categories)) not in block
    ]
    return not missing_entries, missing_entries, None
