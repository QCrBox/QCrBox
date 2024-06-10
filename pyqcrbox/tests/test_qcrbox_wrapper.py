import pytest
from qcrbox_wrapper_new import QCrBoxCommand, QCrBoxWrapper


@pytest.mark.anyio
async def test_qcrbox_wrapper(test_server, test_client):
    """
    QCrBoxWrapper can access registered applications and commands
    """
    with test_server.web_client_sync() as web_client:
        qcrbox = QCrBoxWrapper(web_client)
        apps = qcrbox.applications

        assert len(apps) == 1

        app_info = apps[0]
        assert app_info.name == "Dummy Application"
        assert app_info.slug == "dummy_application"
        assert app_info.version == "x.y.z"

        assert len(app_info.commands) == 1
        cmd = app_info.commands[0]
        assert cmd.name == "greet_and_sleep"
        assert cmd.par_name_list == []


@pytest.mark.anyio
async def test_application_dict(test_server, test_client):
    with test_server.web_client_sync() as web_client:
        qcrbox = QCrBoxWrapper(web_client)
        dummy_app = qcrbox.application_dict["Dummy Application"]

        assert isinstance(dummy_app.greet_and_sleep, QCrBoxCommand)
