"""Tests for typed command return values (output artifacts)."""

from types import SimpleNamespace

import anyio
import pytest

from pyqcrbox.data_management import DataFile
from pyqcrbox.data_management.artifact_kind import ArtifactKind, media_type_for_data_file
from pyqcrbox.registry.client.executable_command.base_calculation import BaseCalculation
from pyqcrbox.sql_models.command_spec.output_spec import BaseArtifactOutputSpec, get_output_spec_from_json
from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import get_declared_outputs

ARTIFACT_DTYPES = {
    "QCrBox.output_text": ("text", "txt"),
    "QCrBox.output_image": ("image", "png"),
    "QCrBox.output_html": ("html", "html"),
    "QCrBox.output_interactive_structure": ("interactive_structure", "cif"),
    "QCrBox.output_interactive_graph": ("interactive_graph", "json"),
}


# --- output specs --------------------------------------------------------------


@pytest.mark.parametrize("dtype,kind_and_ext", ARTIFACT_DTYPES.items())
def test_artifact_output_dtypes_parse_and_carry_their_kind(dtype, kind_and_ext):
    kind, default_ext = kind_and_ext
    spec = get_output_spec_from_json({"name": "out", "dtype": dtype})
    assert isinstance(spec, BaseArtifactOutputSpec)
    assert spec.artifact_kind == kind
    assert spec.required_output is True
    # filename defaults to <name>.<default extension>, but can be fixed in the spec
    assert spec.resolved_filename == f"out.{default_ext}"
    assert get_output_spec_from_json({"name": "out", "dtype": dtype, "filename": "x.dat"}).resolved_filename == "x.dat"
    # the spec kinds must match the ArtifactKind enum used for storage/serving
    assert ArtifactKind(kind).value == kind


def test_required_output_can_be_disabled():
    spec = get_output_spec_from_json({"name": "out", "dtype": "QCrBox.output_text", "required_output": False})
    assert spec.required_output is False


def test_output_cif_spec_carries_entry_fields():
    spec = get_output_spec_from_json(
        {
            "name": "output_cif",
            "dtype": "QCrBox.output_cif",
            "required_entries": ["_cell_length_a", {"one_of": ["_a", "_b"]}],
            "invalidated_entries": ["_refine.*"],
            "output_block": 1,
        }
    )
    assert spec.resolved_filename == "output_cif.cif"
    assert spec.invalidated_entries == ["_refine.*"]
    assert spec.output_block == 1


@pytest.mark.parametrize("bad_filename", ["/etc/passwd", "../escape.txt", "a/../../b.txt"])
def test_output_spec_rejects_path_escapes(bad_filename):
    with pytest.raises(ValueError, match="relative path inside the work directory"):
        get_output_spec_from_json({"name": "report", "dtype": "QCrBox.output_text", "filename": bad_filename})


# --- get_declared_outputs -----------------------------------------------------


def _make_cmd_spec(output_specs):
    return SimpleNamespace(outputs=output_specs)


def test_get_declared_outputs_collects_primary_and_artifacts():
    outputs = get_declared_outputs(
        _make_cmd_spec(
            [
                get_output_spec_from_json(
                    {"name": "output_cif", "dtype": "QCrBox.output_cif", "filename": "result.cif"}
                ),
                get_output_spec_from_json({"name": "report", "dtype": "QCrBox.output_text", "filename": "report.txt"}),
                get_output_spec_from_json(
                    {"name": "graph", "dtype": "QCrBox.output_interactive_graph", "required_output": False}
                ),
            ]
        )
    )
    assert outputs.primary_cif_filename == "result.cif"
    assert [(a.kind, a.filename, a.required_output) for a in outputs.artifacts] == [
        ("text", "report.txt", True),
        ("interactive_graph", "graph.json", False),
    ]


def test_get_declared_outputs_without_outputs():
    outputs = get_declared_outputs(_make_cmd_spec([]))
    assert outputs.primary_cif_filename is None
    assert outputs.artifacts == []


# --- media types --------------------------------------------------------------


@pytest.mark.parametrize(
    "kind,filename,expected",
    [
        ("text", "report.txt", "text/plain"),
        ("html", "report.html", "text/html"),
        ("interactive_structure", "structure.cif", "chemical/x-cif"),
        ("interactive_graph", "graph.json", "application/json"),
        ("image", "img.png", "image/png"),
        ("image", "img.svg", "image/svg+xml"),
        ("image", "img.unknown", "application/octet-stream"),
        (None, "upload.cif", "chemical/x-cif"),
        (None, "notes.txt", "text/plain"),
        # kind-less html must NEVER be served as text/html (no smuggling)
        (None, "page.html", "text/plain"),
        (None, "blob.bin", "application/octet-stream"),
    ],
)
def test_media_type_for_data_file(kind, filename, expected):
    assert media_type_for_data_file(kind, filename) == expected


# --- DataFile.kind metadata compat --------------------------------------------


def test_data_file_kind_roundtrip_and_legacy_compat():
    df = DataFile(qcrbox_file_id="qcrbox_df_0x1", qcrbox_dataset_id=None, filename="a.txt", filetype="txt", kind="text")
    assert DataFile(**df.model_dump()).kind == "text"
    assert df.to_response_model().kind == "text"

    # Legacy KV metadata (stored before the kind field existed) must still parse
    legacy = {"qcrbox_file_id": "qcrbox_df_0x2", "qcrbox_dataset_id": None, "filename": "b.cif", "filetype": "cif"}
    assert DataFile(**legacy).kind is None


# --- save_output_to_data_manager ----------------------------------------------


class FakeDataManager:
    def __init__(self):
        self.imported = []  # (filename, kind)

    async def import_file(self, file_path, *, kind=None, _qcrbox_file_id=None):
        self.imported.append((file_path.name if hasattr(file_path, "name") else str(file_path), kind))
        return f"df_{len(self.imported)}"

    async def create_dataset_from_data_files(self, data_file_ids):
        self.dataset_ids = data_file_ids
        return "qcrbox_ds_0xtest"


class DummyCalculation(BaseCalculation):
    def __init__(self, returned_file=None):
        super().__init__(calculation_id="calc_test", calc_finished_event=anyio.Event())
        self._returned_file = returned_file

    def _get_returned_output_file(self):
        return self._returned_file

    async def wait_until_finished(self):  # pragma: no cover - unused
        pass

    @property
    def status(self):  # pragma: no cover - unused
        return None

    @property
    async def stdout(self):  # pragma: no cover - unused
        return None

    @property
    async def stderr(self):  # pragma: no cover - unused
        return None

    async def terminate(self):  # pragma: no cover - unused
        pass


def _declared(primary=None, artifacts=()):
    from pyqcrbox.sql_models.parameter_spec.base_parameter_spec import DeclaredArtifact, DeclaredOutputs

    return DeclaredOutputs(
        primary_cif_filename=primary,
        artifacts=[DeclaredArtifact(**a) for a in artifacts],
    )


@pytest.mark.anyio
async def test_save_output_collects_primary_and_artifacts(tmp_path):
    (tmp_path / "result.cif").write_text("data_x\n")
    (tmp_path / "report.txt").write_text("hello\n")
    dm = FakeDataManager()
    calc = DummyCalculation(returned_file=tmp_path / "result.cif")
    declared = _declared(artifacts=[{"kind": "text", "filename": "report.txt"}])

    dataset_id = await calc.save_output_to_data_manager(dm, declared_outputs=declared, work_dir=tmp_path)
    assert dataset_id == "qcrbox_ds_0xtest"
    assert dm.imported == [("result.cif", None), ("report.txt", "text")]


@pytest.mark.anyio
async def test_save_output_cli_primary_from_declared_filename(tmp_path):
    # CLI commands return no file; the declared output_cif filename is picked up
    (tmp_path / "out.cif").write_text("data_x\n")
    dm = FakeDataManager()
    calc = DummyCalculation(returned_file=None)

    dataset_id = await calc.save_output_to_data_manager(
        dm, declared_outputs=_declared(primary="out.cif"), work_dir=tmp_path
    )
    assert dataset_id == "qcrbox_ds_0xtest"
    assert dm.imported == [("out.cif", None)]


@pytest.mark.anyio
async def test_save_output_missing_required_artifact_raises(tmp_path):
    dm = FakeDataManager()
    calc = DummyCalculation()
    declared = _declared(artifacts=[{"kind": "text", "filename": "missing.txt"}])
    with pytest.raises(ValueError, match="declared required output"):
        await calc.save_output_to_data_manager(dm, declared_outputs=declared, work_dir=tmp_path)


@pytest.mark.anyio
async def test_save_output_missing_optional_artifact_is_skipped(tmp_path):
    (tmp_path / "report.txt").write_text("hello\n")
    dm = FakeDataManager()
    calc = DummyCalculation()
    declared = _declared(
        artifacts=[
            {"kind": "text", "filename": "report.txt"},
            {"kind": "text", "filename": "missing.txt", "required_output": False},
        ]
    )
    dataset_id = await calc.save_output_to_data_manager(dm, declared_outputs=declared, work_dir=tmp_path)
    assert dataset_id == "qcrbox_ds_0xtest"
    assert dm.imported == [("report.txt", "text")]


@pytest.mark.anyio
async def test_save_output_artifact_only_creates_dataset_without_primary(tmp_path):
    (tmp_path / "graph.json").write_text("{}")
    dm = FakeDataManager()
    calc = DummyCalculation()
    declared = _declared(artifacts=[{"kind": "interactive_graph", "filename": "graph.json"}])
    dataset_id = await calc.save_output_to_data_manager(dm, declared_outputs=declared, work_dir=tmp_path)
    assert dataset_id == "qcrbox_ds_0xtest"
    assert dm.imported == [("graph.json", "interactive_graph")]


@pytest.mark.anyio
async def test_save_output_nothing_to_store_returns_none(tmp_path):
    dm = FakeDataManager()
    calc = DummyCalculation()
    assert await calc.save_output_to_data_manager(dm, declared_outputs=_declared(), work_dir=tmp_path) is None
    assert dm.imported == []


@pytest.mark.anyio
async def test_save_output_filename_collision_is_deduplicated(tmp_path):
    (tmp_path / "result.cif").write_text("data_x\n")
    dm = FakeDataManager()
    calc = DummyCalculation(returned_file=tmp_path / "result.cif")
    # artifact with the same filename as the primary output
    declared = _declared(artifacts=[{"kind": "interactive_structure", "filename": "result.cif"}])
    await calc.save_output_to_data_manager(dm, declared_outputs=declared, work_dir=tmp_path)
    assert dm.imported[0] == ("result.cif", None)
    assert dm.imported[1] == ("result-2.cif", "interactive_structure")


def test_merge_commands_adds_new_command_to_existing_application(clean_registry_db):
    """Re-registration with an added command must not crash.

    The added command arrives as a CommandSpecDB whose parameters/outputs are
    already dicts.
    """
    from pathlib import Path

    from pyqcrbox import sql_models

    yaml_path = (
        Path(__file__).parent.parent.parent / "services" / "applications" / "dummy_cli" / "config_dummy_cli.yaml"
    )
    spec = sql_models.ApplicationSpec.from_yaml_file(str(yaml_path))

    # First registration with a subset of commands
    reduced = spec.model_copy(deep=True)
    reduced.commands = reduced.commands[:2]
    sql_models.ApplicationSpecDB.from_pydantic_model(reduced).save_to_db()

    # Re-registration with the full command list must add the missing commands
    sql_models.ApplicationSpecDB.from_pydantic_model(spec).save_to_db()

    from sqlmodel import select

    from pyqcrbox.settings import settings

    with settings.db.get_session() as session:
        saved = session.exec(select(sql_models.ApplicationSpecDB)).one()
        assert {cmd.name for cmd in saved.commands} == {cmd.name for cmd in spec.commands}
        added = next(cmd for cmd in saved.commands if cmd.name == "generate_report_artifacts")
        assert added.outputs["report_text"]["filename"] == "report.txt"
