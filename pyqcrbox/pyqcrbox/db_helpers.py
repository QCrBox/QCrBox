import sqlalchemy
from sqlmodel import select

from pyqcrbox import settings

__all__ = ["get_one", "get_one_or_none"]


def _build_where_clauses(model_cls, **kwargs):
    return (getattr(model_cls, attr_name) == value for attr_name, value in kwargs.items())


def get_one(model_cls, **kwargs):
    with settings.db.get_session() as session:
        where_clauses = _build_where_clauses(model_cls, **kwargs)
        result = session.exec(select(model_cls).where(*where_clauses)).one()
        return result


def get_one_or_none(model_cls, **kwargs):
    try:
        return get_one(model_cls, **kwargs)
    except sqlalchemy.exc.NoResultFound:
        return None
