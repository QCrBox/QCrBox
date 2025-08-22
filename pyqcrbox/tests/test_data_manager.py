from pathlib import Path

import pytest

from pyqcrbox.data_management import DataManager


@pytest.mark.anyio
async def test_local_file_can_be_imported(data_manager: DataManager, sample_cif_file: Path) -> None:
    """Test that we can import a local file and retrieve its contents from the data file manager."""
    qcrbox_file_id = "qcrbox_data_file_001"
    file_exists = await data_manager.data_file_exists(qcrbox_file_id)
    if file_exists:
        await data_manager.delete_data_file(qcrbox_file_id)

    await data_manager.import_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)
    assert await data_manager.data_file_exists(qcrbox_file_id), "Data file did not import into DataManager"

    stored_file_contents = await data_manager.get_data_file_contents(qcrbox_file_id)
    actual_file_contents = sample_cif_file.read_bytes()
    assert stored_file_contents == actual_file_contents, "Data file in DataManager does not match test file"


@pytest.mark.anyio
async def test_file_can_be_deleted(data_manager: DataManager) -> None:
    """Test that a data file can be deleted."""
    qcrbox_file_id = "qcrbox_data_file_001"
    assert await data_manager.data_file_exists(qcrbox_file_id), "Test data file doesn't exist"

    await data_manager.delete_data_file(qcrbox_file_id)
    assert not await data_manager.data_file_exists(qcrbox_file_id), "Test data file wasn't removed"


@pytest.mark.anyio
async def test_getting_data_files(data_manager: DataManager, sample_cif_file: Path) -> None:
    """Test that we can retrieve a list of stored data files."""
    qcrbox_file_id = "qcrbox_data_file_002"
    await data_manager.import_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)

    data_files = await data_manager.get_data_files()
    num_data_files_start = len(data_files)
    assert num_data_files_start >= 1, "No data files in DataManager"

    qcrbox_file_id = "qcrbox_data_file_002"
    await data_manager.delete_data_file(qcrbox_file_id)
    data_files = await data_manager.get_data_files()
    assert len(data_files) == num_data_files_start - 1, (
        "Incorrect number of data files in DataManager after removing data file"
    )

    await data_manager.import_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)
    data_files = await data_manager.get_data_files()
    assert len(data_files) == num_data_files_start, (
        "Incorrect number of data files in DataManager after importing data file"
    )
    file1 = data_files[-1]
    assert file1.filename == sample_cif_file.name, "Data file does not have correct file name"
    assert file1.qcrbox_file_id == qcrbox_file_id, "Data file does not have correct ID"
    await data_manager.delete_data_file(qcrbox_file_id)


@pytest.mark.anyio
async def test_export_data_file(data_manager: DataManager, sample_cif_file: Path, tmp_path: Path) -> None:
    """Test that exporting a previously imported data file produces the expected file contents."""
    qcrbox_file_id = "qcrbox_data_file_003"
    await data_manager.import_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)

    output_dir = tmp_path / "output"
    output_filename = "output.cif"
    expected_output_file_path = output_dir / output_filename

    exported_file_path = await data_manager.export_data_file(qcrbox_file_id, output_dir, output_filename)
    assert exported_file_path.exists()
    assert exported_file_path == expected_output_file_path

    original_file_contents = sample_cif_file.read_bytes()
    exported_file_contents = exported_file_path.read_bytes()
    assert exported_file_contents == original_file_contents
    await data_manager.delete_data_file(qcrbox_file_id)


@pytest.mark.anyio
async def test_appending_to_dataset(data_manager: DataManager, sample_cif_file: Path, sample_json_file: Path) -> None:
    """Test that we can append a new file to a dataset."""
    # Add test files to the DataManager
    test_file_id_1 = "qcrbox_data_file_append_004"
    data_file_id_1 = await data_manager.import_file(sample_cif_file, _qcrbox_file_id=test_file_id_1)
    assert await data_manager.data_file_exists(test_file_id_1)
    test_file_id_2 = "qcrbox_data_file_append_005"
    data_file_id_2 = await data_manager.import_file(sample_json_file, _qcrbox_file_id=test_file_id_2)
    assert await data_manager.data_file_exists(test_file_id_2)

    # Create dataset with the first test file
    dataset_id = await data_manager.create_dataset_from_data_files(data_file_id_1)

    # Make sure the first file is in there
    dataset = await data_manager.get_dataset(dataset_id)
    assert dataset.first_data_file.qcrbox_file_id == test_file_id_1, (
        f"Data file {test_file_id_1} not in created dataset"
    )

    # Now append another file and check it's in there too
    appended_dataset_id = await data_manager.update_data_file_in_dataset(dataset_id, data_file_id_2)
    assert appended_dataset_id == dataset_id, (
        "Dataset ID returned for appended dataset doesn't match original dataset ID"
    )
    dataset = await data_manager.get_dataset(dataset_id)
    assert dataset.contains_multiple_files, "Dataset doesn't contain multiple files after appending a file to it"
    second_file = dataset.data_files.get(sample_json_file.name, None)
    assert second_file, "Second sample file is not in dataset"
    assert second_file.qcrbox_file_id == test_file_id_2

    await data_manager.delete_data_file(test_file_id_1)
    await data_manager.delete_data_file(test_file_id_2)
