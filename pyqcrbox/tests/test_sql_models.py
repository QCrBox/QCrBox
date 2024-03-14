from sqlmodel import select

from pyqcrbox import settings
from pyqcrbox.sql_models import ApplicationSpecDB, CommandDB, ParameterDB


def test_default_database_url():
    """
    The default database URL should point to an in-memory SQLite database.
    """
    assert settings.db.url == "sqlite:///:memory:"


def test_save_parameter_spec_to_db(tmp_db_url):
    """
    Create parameter specs, save them to the database, retrieve them and check the result.
    """
    with settings.db.get_session(url=tmp_db_url, init_db=True) as session:
        param1 = ParameterDB(name="first_param", type="int")
        param2 = ParameterDB(name="second_param", type="str", description="The second parameter", required=False)
        session.add(param1)
        session.add(param2)
        session.commit()

    with settings.db.get_session(url=tmp_db_url, init_db=False) as session:
        result = session.exec(select(ParameterDB)).all()
        assert 2 == len(result)

        rec_1, rec_2 = result

        assert rec_1.name == "first_param"
        assert rec_1.type == "int"
        assert rec_1.required is True
        assert rec_1.description == ""

        assert rec_2.name == "second_param"
        assert rec_2.type == "str"
        assert rec_2.required is False
        assert rec_2.description == "The second parameter"


def test_save_command_spec_to_db(tmp_db_url):
    """
    Create a command spec, save it to the database, retrieve it and check the result.
    """
    with settings.db.get_session(url=tmp_db_url, init_db=True) as session:
        param1 = ParameterDB(name="cif_path", type="str")
        param2 = ParameterDB(name="ls_cycles", type="int", required=False)  # default_value=5
        param3 = ParameterDB(name="weight_cycles", type="int", required=False)  # default_value=5
        cmd = CommandDB(name="refine_iam", implemented_as="CLI", parameters=[param1, param2, param3])
        session.add(cmd)
        session.commit()

    with settings.db.get_session(url=tmp_db_url) as session:
        result = session.exec(select(CommandDB)).all()
        assert len(result) == 1

        db_cmd = result[0]

        assert db_cmd.name == "refine_iam"
        assert db_cmd.implemented_as == "CLI"

        assert len(db_cmd.parameters) == 3
        assert db_cmd.parameters[0].name == "cif_path"
        assert db_cmd.parameters[1].name == "ls_cycles"
        assert db_cmd.parameters[2].name == "weight_cycles"


def test_save_application_spec_to_db(tmp_db_url):
    """
    Create an application spec, save it to the database, retrieve it and check the result.
    """
    with settings.db.get_session(url=tmp_db_url, init_db=True) as session:
        param1 = ParameterDB(name="cif_path", type="str")
        param2 = ParameterDB(name="ls_cycles", type="int", required=False)  # default_value=5
        param3 = ParameterDB(name="weight_cycles", type="int", required=False)  # default_value=5
        cmd_refine_iam = CommandDB(name="refine_iam", implemented_as="CLI", parameters=[param1, param2, param3])
        application = ApplicationSpecDB(
            name="Olex2",
            slug="olex2_linux",
            version="x.y.z",
            description="Crystallography at your fingertip",
            email="helpdesk@olexsys.org",
            commands=[cmd_refine_iam],
            private_routing_key="my-private_routing-key",
            routing_key_command_invocation="my-app-routing-key",
            cif_entry_sets=[],
        )
        session.add(application)
        session.commit()

    with settings.db.get_session(url=tmp_db_url) as session:
        result = session.exec(select(ApplicationSpecDB)).all()
        assert len(result) == 1
        db_application = result[0]

        assert db_application.name == "Olex2"
        assert db_application.version == "x.y.z"

        assert len(db_application.commands) == 1
        db_cmd = db_application.commands[0]
        assert db_cmd.name == "refine_iam"

        assert db_cmd.parameters[0].name == "cif_path"
        assert db_cmd.parameters[1].name == "ls_cycles"
        assert db_cmd.parameters[2].name == "weight_cycles"
