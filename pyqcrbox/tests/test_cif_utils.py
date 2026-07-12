"""Tests for unified-CIF conversion on upload and the can-run checks."""

from pathlib import Path

import pytest

from pyqcrbox import sql_models
from pyqcrbox.registry.server.api import cif_utils
from pyqcrbox.registry.server.api.cif_utils import CifConversionError

pytest.importorskip("qcrboxtools")

TEST_DATA_DIR = Path(__file__).parent.parent / "robot_tests" / "test_data"
DUMMY_CLI_SPEC_FILE = (
    Path(__file__).parent.parent.parent / "services" / "applications" / "dummy_cli" / "config_dummy_cli.yaml"
)

UNIFIED_CIF = b"""data_test
_cell.length_a 10.0
_cell.length_a_su 0.03
_cell.length_b 12.0
_cell.length_c 14.0
_cell.angle_alpha 90.0
_cell.angle_beta 90.0
_cell.angle_gamma 90.0
_chemical.formula_sum 'C2 H6 O'
"""


# --- to_unified_cif_bytes -----------------------------------------------------


def test_cif_content_is_converted_to_unified_regardless_of_extension():
    from qcrboxtools.cif.cif2cif import bytes_to_unified_if_cif

    original = TEST_DATA_DIR.joinpath("to_unified_test_cif.cif").read_bytes()
    expected = bytes_to_unified_if_cif(original)
    assert cif_utils.to_unified_cif_bytes(original, "upload.cif") == expected
    # extension does not matter - .fcf and vendor dialects are converted too
    assert cif_utils.to_unified_cif_bytes(original, "upload.fcf") == expected
    assert expected != original  # sanity: the test file is not already unified


def test_old_style_su_values_are_split():
    converted = cif_utils.to_unified_cif_bytes(b"data_x\n_cell_length_a 5.4321(3)\n", "x.cif")
    assert b"_cell.length_a" in converted
    assert b"_cell.length_a_su" in converted


def test_non_cif_content_passes_through_unchanged():
    binary = b"\x89PNG\r\n\x1a\n\x00\x01\x02"
    assert cif_utils.to_unified_cif_bytes(binary, "image.png") == binary
    json_text = b'{"some": "json"}'
    assert cif_utils.to_unified_cif_bytes(json_text, "data.json") == json_text


def test_malformed_cif_raises_conversion_error():
    malformed = b"data_x\nloop_\n_a\n_b\n1\n"  # wrong number of loop items
    with pytest.raises(CifConversionError, match="looks like a CIF file"):
        cif_utils.to_unified_cif_bytes(malformed, "broken.cif")


# --- can-run checks -----------------------------------------------------------


@pytest.fixture(scope="module")
def unified_block():
    block = cif_utils.parse_cif_first_block(UNIFIED_CIF)
    assert block is not None
    return block


def test_parse_first_block_returns_none_for_non_cif():
    assert cif_utils.parse_cif_first_block(b"\x00\x01binary") is None
    assert cif_utils.parse_cif_first_block(b"just some text\n") is None


def test_command_without_cif_parameter_can_always_run(unified_block):
    parameters = {"some_number": {"dtype": "int"}}
    assert cif_utils.check_command_can_run(parameters, {}, unified_block) == (True, [], None)


def test_cif_parameter_without_entry_requirements_can_run(unified_block):
    parameters = {"input_cif": {"dtype": "QCrBox.cif_data_file"}}
    can_run, missing, reason = cif_utils.check_command_can_run(parameters, {}, unified_block)
    assert (can_run, missing, reason) == (True, [], None)


def test_missing_required_entries_are_reported(unified_block):
    parameters = {
        "input_cif": {
            "dtype": "QCrBox.cif_data_file",
            "required_entries": ["_cell.length_a", "_atom_site.fract_x"],
        }
    }
    can_run, missing, reason = cif_utils.check_command_can_run(parameters, {}, unified_block)
    assert can_run is False
    assert missing == ["_atom_site.fract_x"]
    assert reason is None


def test_satisfied_required_entries_can_run(unified_block):
    parameters = {
        "input_cif": {
            "dtype": "QCrBox.cif_data_file",
            "required_entries": ["_cell.length_a", "_cell.length_b"],
        }
    }
    assert cif_utils.check_command_can_run(parameters, {}, unified_block)[0] is True


def test_entry_sets_are_resolved(unified_block):
    entry_sets = cif_utils.entry_sets_by_name(
        [{"name": "cell", "required": ["_cell.length_a", "_cell.angle_alpha"], "optional": []}]
    )
    parameters = {
        "input_cif": {"dtype": "QCrBox.cif_data_file", "required_entry_sets": ["cell"]}
    }
    assert cif_utils.check_command_can_run(parameters, entry_sets, unified_block)[0] is True

    entry_sets_missing = cif_utils.entry_sets_by_name(
        [{"name": "cell", "required": ["_atom_site.fract_x"], "optional": []}]
    )
    can_run, missing, _ = cif_utils.check_command_can_run(parameters, entry_sets_missing, unified_block)
    assert can_run is False
    assert missing == ["_atom_site.fract_x"]


def test_unknown_entry_set_fails_open_with_reason(unified_block):
    parameters = {
        "input_cif": {"dtype": "QCrBox.cif_data_file", "required_entry_sets": ["not_registered"]}
    }
    can_run, missing, reason = cif_utils.check_command_can_run(parameters, {}, unified_block)
    assert can_run is True
    assert "re-registration" in reason


def test_one_of_entries_are_resolved(unified_block):
    parameters = {
        "input_cif": {
            "dtype": "QCrBox.cif_data_file",
            "required_entries": [{"one_of": ["_cell.length_a", "_atom_site.fract_x"]}],
        }
    }
    assert cif_utils.check_command_can_run(parameters, {}, unified_block)[0] is True

    parameters_unresolvable = {
        "input_cif": {
            "dtype": "QCrBox.cif_data_file",
            "required_entries": [{"one_of": ["_atom_site.fract_x", "_atom_site.fract_y"]}],
        }
    }
    can_run, missing, _ = cif_utils.check_command_can_run(parameters_unresolvable, {}, unified_block)
    assert can_run is False
    assert missing


def test_unparseable_file_blocks_cif_commands_only():
    parameters_with_cif = {"input_cif": {"dtype": "QCrBox.cif_data_file"}}
    can_run, _, reason = cif_utils.check_command_can_run(parameters_with_cif, {}, block=None)
    assert can_run is False
    assert reason == "not a parseable CIF file"

    parameters_without_cif = {"some_number": {"dtype": "int"}}
    assert cif_utils.check_command_can_run(parameters_without_cif, {}, block=None)[0] is True


# --- cif_entry_sets persistence -----------------------------------------------


def test_application_cif_entry_sets_round_trip(clean_registry_db):
    spec = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    assert spec.cif_entry_sets, "test premise: dummy_cli spec declares cif_entry_sets"

    saved = sql_models.ApplicationSpecDB.from_pydantic_model(spec).save_to_db()
    stored_names = {entry_set["name"] for entry_set in saved.cif_entry_sets}
    assert "cell_elements" in stored_names

    # Re-registration with changed entry sets updates the stored value
    spec_updated = sql_models.ApplicationSpec.from_yaml_file(DUMMY_CLI_SPEC_FILE)
    spec_updated.cif_entry_sets = spec_updated.cif_entry_sets[:1]
    saved_again = sql_models.ApplicationSpecDB.from_pydantic_model(spec_updated).save_to_db()
    assert saved_again.id == saved.id
    assert len(saved_again.cif_entry_sets) == 1
