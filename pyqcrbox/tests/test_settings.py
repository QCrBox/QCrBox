from sqlmodel import select

from pyqcrbox import settings
from pyqcrbox.sql_models import CommandSpecDB, ParameterSpecDB


def test_default_database_url():
    """
    The default database URL should point to an in-memory SQLite database.
    """
    assert settings.db.url == "sqlite:///:memory:"


def test_save_parameters_to_db(tmp_db_url):
    """
    Create a couple of parameter specs, save them to the database, retrieve them again and verify the result.
    """
    with settings.db.get_session(url=tmp_db_url, init_db=True) as session:
        param1 = ParameterSpecDB(name="first_param", dtype="int")
        param2 = ParameterSpecDB(name="second_param", dtype="str", description="The second parameter", required=False)
        session.add(param1)
        session.add(param2)
        session.commit()

    with settings.db.get_session(url=tmp_db_url, init_db=False) as session:
        result = session.exec(select(ParameterSpecDB)).all()
        assert 2 == len(result)

        rec_1, rec_2 = result

        assert rec_1.name == "first_param"
        assert rec_1.dtype == "int"
        assert rec_1.required is True
        assert rec_1.description == ""

        assert rec_2.name == "second_param"
        assert rec_2.dtype == "str"
        assert rec_2.required is False
        assert rec_2.description == "The second parameter"


def test_save_command_to_db(tmp_db_url):
    """
    Create a command spec and save it to the database.
    """
    with settings.db.get_session(url=tmp_db_url, init_db=True) as session:
        param1 = ParameterSpecDB(name="cif_path", dtype="str")
        param2 = ParameterSpecDB(name="ls_cycles", dtype="int", required=False)  # default_value=5
        param3 = ParameterSpecDB(name="weight_cycles", dtype="int", required=False)  # default_value=5
        cmd = CommandSpecDB(name="refine_iam", implemented_as="CLI", parameters=[param1, param2, param3])
        session.add(cmd)
        session.commit()

    with settings.db.get_session(url=tmp_db_url) as session:
        result = session.exec(select(CommandSpecDB)).all()
        assert len(result) == 1

        rec_1 = result[0]

        assert rec_1.name == "refine_iam"
        assert rec_1.implemented_as == "CLI"

        assert len(rec_1.parameters) == 3
        assert rec_1.parameters[0].name == "cif_path"
        assert rec_1.parameters[1].name == "ls_cycles"
        assert rec_1.parameters[2].name == "weight_cycles"
