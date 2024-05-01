import pytest

from pyqcrbox import msg_specs, settings


@pytest.mark.anyio
async def test_invoke_command(
    rabbit_test_broker,
    test_server,
    test_client,
    # sample_application_spec,
):
    routing_key_qcrbox_registry = settings.rabbitmq.routing_key_qcrbox_registry
    # private_routing_key = "qcrbox_rk_test_client_xyz"

    msg_invoke_cmd = msg_specs.InvokeCommand(
        action="invoke_command",
        payload=msg_specs.PayloadForInvokeCommand(
            application_slug="dummy_application",
            application_version="x.y.z",
            command_name="say_hello",
            arguments={},
        ),
    )

    rabbit_test_broker.publish(msg_invoke_cmd, routing_key_qcrbox_registry)
    assert False, "TODO: implement the remainder of the test"
