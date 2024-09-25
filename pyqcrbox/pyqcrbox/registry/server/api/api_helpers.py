from sqlmodel import select

from pyqcrbox import settings, sql_models


def _retrieve_applications() -> list[sql_models.ApplicationSpecWithCommands]:
    """
    Retrieves list of registered applications from the database.
    """
    model_cls = sql_models.ApplicationSpecDB
    # filter_clauses = construct_filter_clauses(model_cls, slug=slug, version=version)

    with settings.db.get_session() as session:
        # applications = session.scalars(select(model_cls).where(*filter_clauses)).all()
        applications = session.scalars(select(model_cls)).all()
        applications_response_models = [app.to_response_model() for app in applications]

    return applications_response_models


def _retrieve_commands() -> list[sql_models.CommandSpecWithParameters]:
    """
    Retrieves list of commands from the database.
    """
    # model_cls = sql_models.CommandSpecDB
    # filter_clauses = [
    #     (name is None) or (model_cls.name == name),
    #     (application_slug is None) or (sql_models.ApplicationSpecDB.slug == application_slug),
    #     (application_version is None) or (sql_models.ApplicationSpecDB.version == application_version),
    # ]
    stmt = select(
        sql_models.CommandSpecDB, sql_models.ApplicationSpecDB.slug, sql_models.ApplicationSpecDB.version
    ).join(
        sql_models.CommandSpecDB.application,
    )

    with settings.db.get_session() as session:
        # commands = session.scalars(select(model_cls).where(*filter_clauses)).all()
        commands = session.scalars(stmt).all()
        commands = [cmd.to_response_model() for cmd in commands]

    return commands
