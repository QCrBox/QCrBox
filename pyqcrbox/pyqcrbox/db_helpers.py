import sqlalchemy
from sqlmodel import and_, select

from pyqcrbox import settings

__all__ = ["get_one", "get_one_or_none"]


def get_one(model_cls, **kwargs):
    with settings.db.get_session() as session:
        conditions = [getattr(model_cls, attr_name) == value for attr_name, value in kwargs.items()]
        result = session.exec(select(model_cls).where(and_(*conditions))).one()
        return result


def get_one_or_none(model_cls, **kwargs):
    try:
        return get_one(model_cls, **kwargs)
    except sqlalchemy.exc.NoResultFound:
        return None


def get_first_or_none(model_cls):
    with settings.db.get_session() as session:
        return session.exec(select(model_cls)).first()


def table_is_empty(model_cls):
    return get_first_or_none(model_cls) is None
