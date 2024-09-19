import pytest

from pyqcrbox.services import get_data_file_manager


@pytest.mark.anyio
async def test_import_of_local_file(sample_cif_file):
    """
    Test that we can import a local file and retrieve its contents from the data file manager.
    """
    data_file_manager = await get_data_file_manager()

    qcrbox_file_id = "qcrbox_data_file_001"
    assert not await data_file_manager.exists(qcrbox_file_id)

    await data_file_manager.import_local_file(sample_cif_file, _qcrbox_file_id=qcrbox_file_id)
    assert await data_file_manager.exists(qcrbox_file_id)

    file_contents = await data_file_manager.read_file(qcrbox_file_id)
    assert file_contents == sample_cif_file.read_text()
