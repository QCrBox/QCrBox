import pytest

from pyqcrbox import msg_specs


@pytest.mark.anyio
async def test_rabbitmq_message(provide_test_server, provide_test_client, sample_application_spec):
    private_routing_key = "qcrbox_rk_test_client_xyz"

    test_server = provide_test_server()
    test_client = provide_test_client(private_routing_key=private_routing_key)

    async with test_server.run():
        assert not test_server.get_mock_handler("qcrbox-registry").called

        async with test_client.run():
            # we don't need to explicitly do anything here because we're testing the startup process,
            # which is already triggered
            pass

    expected_registration_message = msg_specs.RegisterApplication(
        action="register_application",
        payload=msg_specs.PayloadForRegisterApplication(
            application_spec=sample_application_spec,
            private_routing_key=private_routing_key,
        ),
    ).dict()
    assert test_server.get_mock_handler("qcrbox-registry").called_once_with(expected_registration_message)
