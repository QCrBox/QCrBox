import pytest


@pytest.mark.anyio
async def test_import_of_local_file(data_manager, sample_cif_file):
    """Test that we can import a local file and retrieve its contents from the data file manager."""
    qcrbox_file_id = "qcrbox_data_file_001"
    await data_manager.delete_data_file(qcrbox_file_id)
    assert not await data_manager.data_file_exists(qcrbox_file_id)

    await data_manager.import_local_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)
    assert await data_manager.data_file_exists(qcrbox_file_id)

    stored_file_contents = await data_manager.get_file_contents(qcrbox_file_id)
    actual_file_contents = sample_cif_file.read_bytes()
    assert stored_file_contents == actual_file_contents


@pytest.mark.anyio
async def test_list_existing_data_files(data_manager, sample_cif_file):
    """Test that we can retrieve a list of stored data files."""
    data_files = await data_manager.get_data_files()
    num_data_files_start = len(data_files)
    assert num_data_files_start >= 1

    qcrbox_file_id = "qcrbox_data_file_001"
    await data_manager.delete_data_file(qcrbox_file_id)
    data_files = await data_manager.get_data_files()
    assert len(data_files) == num_data_files_start - 1

    await data_manager.import_local_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)
    data_files = await data_manager.get_data_files()
    assert len(data_files) == num_data_files_start
    file1 = data_files[-1]
    assert file1.filename == sample_cif_file.name
    assert file1.qcrbox_file_id == qcrbox_file_id
    await data_manager.delete_data_file(qcrbox_file_id)


@pytest.mark.anyio
async def test_export_data_file(data_manager, sample_cif_file, tmp_path):
    """Test that exporting a previously imported data file produces the expected file contents."""
    qcrbox_file_id = "qcrbox_data_file_001"
    await data_manager.import_local_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)

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
