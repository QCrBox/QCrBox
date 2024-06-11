import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from pyqcrbox import sql_models


@pytest.mark.anyio
async def test_command_invocation(
    test_server,
    test_client,
    server_public_queue_name,
):
    """
    POST request to `/commands/invoke` returns response 'ok' with `calculation_id` in payload.
    """
    app = test_client.application_spec
    cmd = app.commands[0]

    payload = sql_models.CommandInvocationCreate(
        application_slug=app.slug,
        application_version=app.version,
        command_name=cmd.name,
        arguments={},
    ).model_dump()

    async with test_server.web_client() as web_client:
        response = await web_client.post("/commands/invoke", json=payload)
        assert response.status_code == HTTP_201_CREATED

        expected_response = {
            "status": "ok",
            "msg": "Accepted command invocation request",
            "payload": {"calculation_id": 1},
        }
        assert expected_response == response.json()


@pytest.mark.anyio
async def test_calculation_status(
    test_server,
    sample_application_spec,
):
    """
    GET request to /calculations/<id> returns status info about the calculation
    """
    app = sample_application_spec
    cmd = app.commands[0]

    payload = sql_models.CommandInvocationCreate(
        application_slug=app.slug,
        application_version=app.version,
        command_name=cmd.name,
        arguments={},
    ).model_dump()

    async with test_server.web_client() as web_client:
        invocation_response = await web_client.post("/commands/invoke", json=payload)
        calculation_id = invocation_response.json()["payload"]["calculation_id"]

        calc_info_response = await web_client.get(f"/calculations/{calculation_id}")
        assert calc_info_response.status_code == HTTP_200_OK

        expected_response = {
            "id": calculation_id,
            "status": "received",
        }
        assert expected_response == calc_info_response.json()
