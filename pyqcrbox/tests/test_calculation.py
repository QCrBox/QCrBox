import pytest

from pyqcrbox import sql_models


@pytest.fixture
def dummy_calculation(test_server, test_client):
    app = test_client.application_spec
    cmd = app.commands[0]

    calc = sql_models.CalculationDB(
        application_slug=app.slug,
        application_version=app.version,
        command_name=cmd.name,
        arguments={},
        correlation_id="dummy_correlation_id",
    )
    return calc


@pytest.mark.anyio
async def test_calculation_status_update(dummy_calculation):
    assert dummy_calculation.status == "received"

    dummy_calculation.save_to_db()
    assert dummy_calculation.status == "received"

    dummy_calculation.update_status("running")
    assert dummy_calculation.status == "running"

    with pytest.raises(ValueError):
        dummy_calculation.update_status("<THIS_STATUS_IS_INVALID>")
