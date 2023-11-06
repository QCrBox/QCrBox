import os

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine, Session
from .sql_models import QCrBoxBaseSQLModel, KeywordDB

connect_args = {"check_same_thread": False}
registry_db_dir = os.environ.get("QCRBOX_REGISTRY_SERVER_DB_DIR", "/mnt/qcrbox_registry_data/")
sqlite_file_name = os.path.join(registry_db_dir, "qcrbox_registry_database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


def create_db_and_tables():
    logger.debug(f"SQLite file name: {sqlite_file_name}")
    logger.debug("Creating database tables if they don't exist yet.")

    # While we're in the prototyping/demo phase, we purge any existing records
    # whenever the registry server starts up. Down the line, we probably want
    # to do something smarter where we check if any existing registered applications
    # are still active and only purge records that are stale.
    QCrBoxBaseSQLModel.metadata.drop_all(engine)

    QCrBoxBaseSQLModel.metadata.create_all(engine)


def seed_database():
    logger.debug("Adding 'officially supported' keywords.")
    try:
        with Session(engine) as session:
            session.add(KeywordDB(text="Atomic Form Factors"))
            session.commit()
    except IntegrityError as exc:
        logger.debug("Keyword already present.")
    logger.debug("Done.")
