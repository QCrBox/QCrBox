import pytest
from qcrbox_wrapper_new.qcrbox_wrapper import QCrBoxWrapper


@pytest.mark.anyio
async def test_qcrbox_wrapper(test_server, test_client):
    """
    QCrBoxWrapper can access registered applications and commands
    """
    async with test_server.web_client() as web_client:
        qcrbox = QCrBoxWrapper(web_client)
        apps = await qcrbox.applications

        assert len(apps) == 1

        app_info = apps[0]
        assert app_info.name == "Dummy Application"
        assert app_info.slug == "dummy_application"
        assert app_info.version == "x.y.z"

        assert len(app_info.commands) == 1
        cmd = app_info.commands[0]
        assert cmd.name == "say_hello"
        assert cmd.par_name_list == []
