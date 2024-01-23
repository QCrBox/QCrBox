import os
import sqlite3
from typing import Optional

from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine, Session, select
from qcrbox.common.msg_specs.sql_models import QCrBoxBaseSQLModel, KeywordDB
from qcrbox.common import sql_models

connect_args = {"check_same_thread": False}
registry_db_dir = os.environ.get("QCRBOX_REGISTRY_DB_DIR", "/mnt/qcrbox/qcrbox_registry_data/")

sqlite_file_name = os.path.join(registry_db_dir, "qcrbox_registry_database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        # ensure that foreign key constraints are enforced
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_and_tables():
    if not os.path.exists(registry_db_dir):
        logger.debug(f"Creating registry database directory: {registry_db_dir}")
        os.makedirs(registry_db_dir, exist_ok=True)

    logger.debug(f"SQLite file name: {sqlite_file_name}")
    logger.debug("Creating database tables if they don't exist yet.")

    # While we're in the prototyping/demo phase, we purge any existing records
    # whenever the registry server starts up. Down the line, we probably want
    # to do something smarter where we check if any existing registered applications
    # are still active and only purge records that are stale.
    #QCrBoxBaseSQLModel.metadata.drop_all(engine)

    QCrBoxBaseSQLModel.metadata.create_all(engine)


def seed_database():
    logger.debug("Adding 'officially supported' keywords.")
    try:
        with Session(engine) as session:
            session.add(KeywordDB(text="Atomic Form Factors"))
            session.commit()
    except IntegrityError:
        logger.debug("Keyword already present.")
    logger.debug("Done.")


def retrieve_application(name, version):
    from qcrbox.common.msg_specs.sql_models import QCrBoxApplicationDB as cls

    with Session(engine) as session:
        result = session.exec(select(cls).where(cls.name == name, cls.version == version)).one()
        return result


def retrieve_command(name: str, parameters, application_id: int):
    from qcrbox.common.msg_specs.sql_models import QCrBoxCommandDB as cls

    with Session(engine) as session:
        result = session.exec(
            select(cls).where(cls.name == name, cls.parameters == parameters, cls.application_id == application_id)
        ).one()
        return result


def retrieve_container(container_id: int):
    from qcrbox.common.msg_specs.sql_models import QCrBoxContainerDB as cls

    with Session(engine) as session:
        result = session.exec(select(cls).where(cls.id == container_id)).one()
        return result


def retrieve_containers(application_id: Optional[int] = None, command_id: Optional[int] = None):
    if command_id is not None:
        raise NotImplementedError("Filtering by command_id is not implemented yet.")

    with Session(engine) as session:
        stmt = select(sql_models.QCrBoxContainerDB)
        if application_id is not None:
            stmt = stmt.where(sql_models.QCrBoxContainerDB.application_id == application_id)
        # if command_id is not None:
        #     stmt = stmt.where(command_id in sql_models.QCrBoxContainerDB.commands)
        result = session.exec(stmt).all()
        return result
