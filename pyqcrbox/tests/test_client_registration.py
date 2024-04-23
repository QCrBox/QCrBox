import pytest

from pyqcrbox import msg_specs


@pytest.mark.xfail(reason="Client startup not fully implemented yet")
@pytest.mark.anyio
async def test_client_registers_itself_with_server_during_startup(
    test_server,
    create_qcrbox_test_client,
    sample_application_spec,
):
    private_routing_key = "qcrbox_rk_test_client_xyz"
    expected_registration_message = msg_specs.RegisterApplication(
        action="register_application",
        payload=msg_specs.PayloadForRegisterApplication(
            application_spec=sample_application_spec,
            private_routing_key=private_routing_key,
        ),
    ).dict()
    expected_server_response = {"response_to": "register_application", "status": "success"}

    assert not test_server.get_mock_handler("qcrbox-registry").called

    async with create_qcrbox_test_client(private_routing_key=private_routing_key) as test_client:
        test_server.get_mock_handler("qcrbox-registry").assert_called_once_with(expected_registration_message)
        test_client.get_mock_handler(private_routing_key).assert_called_once_with(expected_server_response)
