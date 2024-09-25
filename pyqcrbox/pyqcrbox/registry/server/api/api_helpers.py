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
