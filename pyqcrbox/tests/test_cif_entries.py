"""Tests for spec-model-driven CIF entry resolution (pyqcrbox.cif_entries).

The resolution logic itself is pure Python (qcrboxtools is only needed for
the actual CIF operations), so these tests run everywhere.
"""

import pytest

from pyqcrbox.cif_entries import (
    NoEntriesDeclaredError,
    UnknownEntrySetError,
    entry_sets_by_name,
    input_settings_from_spec,
    output_settings_from_spec,
)
from pyqcrbox.sql_models.cif_entry_set import CifEntrySet

ENTRY_SETS = entry_sets_by_name(
    [
        {"name": "cell", "required": ["_cell_length_a", "_cell_length_b"], "optional": ["_cell_volume"]},
        {"name": "extras", "required": ["_extra_required"], "optional": ["_extra_optional"]},
    ]
)


def test_entry_sets_by_name_accepts_models_and_dicts():
    from_models = entry_sets_by_name([CifEntrySet(name="cell", required=["_a"], optional=["_b"])])
    assert from_models == {"cell": {"required": ["_a"], "optional": ["_b"]}}


def test_input_settings_resolve_sets_and_literals():
    settings = input_settings_from_spec(
        {
            "required_entries": ["_atom_site_label", {"one_of": ["_x", "_y"]}],
            "required_entry_sets": ["cell"],
            "optional_entry_sets": ["extras"],
            "custom_categories": ["shelx"],
            "merge_su": True,
        },
        ENTRY_SETS,
    )
    assert settings.required_entries == [
        "_atom_site_label",
        {"one_of": ["_x", "_y"]},
        "_cell_length_a",
        "_cell_length_b",
    ]
    # optional set contents (required AND optional) are all optional; the
    # required set's optional entries are optional as well
    assert settings.optional_entries == ["_cell_volume", "_extra_required", "_extra_optional"]
    assert settings.custom_categories == ["shelx"]
    assert settings.merge_su is True


def test_required_entries_win_over_optional_duplicates():
    settings = input_settings_from_spec(
        {"required_entries": ["_a"], "optional_entries": ["_a", "_b"]},
        {},
    )
    assert settings.required_entries == ["_a"]
    assert settings.optional_entries == ["_b"]


def test_no_declared_entries_raises():
    with pytest.raises(NoEntriesDeclaredError):
        input_settings_from_spec({"merge_su": True}, {})
    with pytest.raises(NoEntriesDeclaredError):
        output_settings_from_spec({}, {})


def test_unknown_entry_set_raises():
    with pytest.raises(UnknownEntrySetError, match="not_defined"):
        input_settings_from_spec({"required_entry_sets": ["not_defined"]}, ENTRY_SETS)


def test_output_settings_include_invalidated_and_block():
    settings = output_settings_from_spec(
        {
            "required_entry_sets": ["cell"],
            "invalidated_entries": ["_refine.*", "_refine.*"],
            "output_block": 2,
        },
        ENTRY_SETS,
    )
    assert settings.invalidated_entries == ["_refine.*"]
    assert settings.select_block == "2"
    assert "_cell_length_a" in settings.required_entries


def test_settings_accept_pydantic_specs():
    from pyqcrbox.sql_models.command_spec.output_spec import get_output_spec_from_json

    output_spec = get_output_spec_from_json(
        {"name": "output_cif", "dtype": "QCrBox.output_cif", "required_entry_sets": ["cell"]}
    )
    settings = output_settings_from_spec(output_spec, ENTRY_SETS)
    assert settings.required_entries == ["_cell_length_a", "_cell_length_b"]
