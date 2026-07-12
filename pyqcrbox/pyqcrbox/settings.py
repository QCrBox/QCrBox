import functools
import logging
import sys
from enum import Enum
from typing import Any

import sqlalchemy
import sqlmodel
from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine

__all__ = ["StructlogRendererEnum", "get_log_level_as_int", "settings"]


SQLiteDsn = str  # alias for readability
IS_RUNNING_INSIDE_TESTS = hasattr(sys, "_qcrbox_running_inside_tests")
IS_RUNNING_DEBUG_MODE = True


def get_log_level_as_int(level: str):
    mapping = logging.getLevelNamesMapping()
    return mapping[level]


@functools.lru_cache
def create_sqlmodel_engine(url: SQLiteDsn | None, echo: bool, connect_args: tuple[(str, Any)]):
    return create_engine(str(url), echo=echo, connect_args=connect_args)


@functools.lru_cache
def _create_db_tables(engine, purge_existing: bool):
    from pyqcrbox.logging import logger
    from pyqcrbox.sql_models import QCrBoxBaseSQLModel  # import here to avoid a circular import

    logger.debug(f"Initialising the database for engine: {engine}")
    if purge_existing:
        logger.debug("Purging existing tables.")
        QCrBoxBaseSQLModel.metadata.drop_all(engine)
    QCrBoxBaseSQLModel.metadata.create_all(engine)


# Columns added to pre-existing tables after the registry database became
# file-backed. `metadata.create_all` only creates missing tables, so these
# are applied via ALTER TABLE (there is no migration tooling like Alembic).
# Format: (table, column, ddl_type, backfill_sql_or_None).
_LIGHTWEIGHT_MIGRATIONS = [
    ("application", "docker_image", "VARCHAR", None),
    (
        "application",
        "cif_entry_sets",
        "JSON",
        "UPDATE application SET cif_entry_sets = '[]' WHERE cif_entry_sets IS NULL",
    ),
    ("container_instance", "docker_container_id", "VARCHAR", None),
    ("container_instance", "gui_host", "VARCHAR", None),
    (
        "container_instance",
        "status_changed_at",
        "DATETIME",
        "UPDATE container_instance SET status_changed_at = last_seen WHERE status_changed_at IS NULL",
    ),
]


def apply_lightweight_migrations(engine) -> None:
    from pyqcrbox.logging import logger

    with engine.connect() as conn:
        for table, column, ddl_type, backfill_sql in _LIGHTWEIGHT_MIGRATIONS:
            existing_columns = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if existing_columns and column not in existing_columns:
                logger.info(f"Adding missing column {column!r} to table {table!r}")
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                if backfill_sql:
                    conn.exec_driver_sql(backfill_sql)
        conn.commit()


class QCrBoxSettingsBaseModel(BaseSettings):
    model_config = SettingsConfigDict(
        validate_assignment=True,
    )


class DatabaseSettings(QCrBoxSettingsBaseModel):
    url: SQLiteDsn = "sqlite:///:memory:"
    connect_args: dict = {"check_same_thread": False}
    echo: bool = False
    max_desc_length: int = 1023
    max_text_length: int = 255

    def create_db_and_tables(
        self,
        url: SQLiteDsn | None = None,
        echo: bool | None = None,
        purge_existing_tables: bool = False,
    ) -> None:
        engine = self.get_engine(url=url, echo=echo)
        _create_db_tables(engine, purge_existing_tables)

    def get_engine(self, url: SQLiteDsn | None = None, echo: bool | None = None) -> sqlalchemy.Engine:
        url = url if url is not None else self.url
        echo = echo if echo is not None else self.echo
        return create_sqlmodel_engine(url=url, echo=echo, connect_args=tuple(self.connect_args.items()))

    def get_session(
        self,
        url: SQLiteDsn | None = None,
        echo: bool | None = None,
        init_db: bool = False,
        purge_existing_tables: bool = False,
    ) -> sqlmodel.Session:
        engine = self.get_engine(url=url, echo=echo)
        if init_db:
            _create_db_tables(engine, purge_existing_tables)
        return Session(engine)


class NATSSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 4222
    rpc_timeout: float = 3  # seconds
    graceful_timeout: int = 10  # seconds
    max_reconnect_attempts: int = 1

    @computed_field  # type: ignore
    @property
    def url(self) -> str:
        return f"nats://{self.host}:{self.port}/"


class SeverSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 11000
    enable_autoreload: bool = False
    instance_sweep_interval: float = 10.0  # seconds
    instance_stale_after: float = 15.0  # seconds without heartbeat before an instance is marked 'gone'

    @computed_field  # type: ignore
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}/api"


class ClientSettings(QCrBoxSettingsBaseModel):
    host: str = "127.0.0.1"
    port: int = 8002
    keep_calc_work_dir: bool = True
    heartbeat_interval: float = 5.0  # seconds


class RegistrySettings(QCrBoxSettingsBaseModel):
    server: SeverSettings = SeverSettings()
    client: ClientSettings = ClientSettings()


class OrchestratorSettings(QCrBoxSettingsBaseModel):
    enabled: bool = False
    docker_host: str = "http://qcrbox-docker-socket-proxy:2375"
    spawn_timeout: float = 90.0  # seconds to wait for a spawned client to register
    poll_interval: float = 0.5  # seconds between registration polls while spawning
    max_instances_per_app: int = 3  # quota guard for explicit instance creation
    max_instances_per_user: int = 5  # live instances per owner, across applications
    max_total_instances: int | None = None  # global cap on live spawned instances (None = unlimited)
    # Per-container resource limits for spawned instances (None = unlimited).
    container_memory_limit_mb: int | None = None
    container_cpu_limit: float | None = None  # in CPUs, e.g. 4 or 1.5
    container_pids_limit: int | None = None

    @field_validator(
        "max_total_instances",
        "container_memory_limit_mb",
        "container_cpu_limit",
        "container_pids_limit",
        mode="before",
    )
    @classmethod
    def _empty_env_var_means_unlimited(cls, value):
        # These are passed through docker compose as `${VAR:-}`, which yields
        # an empty string when unset.
        if value == "":
            return None
        return value
    idle_timeout: float = 1800.0  # seconds an orchestrator-spawned instance may sit idle before reaping
    gone_retention: float = 3600.0  # seconds before 'gone' instance rows are purged
    network_name: str | None = None  # discovered from the registry's own container if unset
    fallback_network_name: str = "qcrbox_qcrbox-net"
    nats_host: str = "qcrbox-nats"
    registry_host: str = "qcrbox-registry"
    registry_port: int = 8000
    use_syslog_logging: bool = True
    syslog_address: str = "udp://127.0.0.1:514"
    label_prefix: str = "org.qcrbox"
    # Per-instance GUI routing (interactive applications): spawned GUI containers
    # get a Traefik route at https://<slug>-<id>.gui.<gui_domain>/ (covered by the
    # Authelia wildcard rule for *.gui.<domain>).
    gui_domain: str = "qcrbox.localhost"
    gui_container_port: int = 8080  # noVNC port exposed by base_novnc images


class AuthSettings(QCrBoxSettingsBaseModel):
    # Shared secret authorising trusted services (e.g. the web frontend) to act
    # on behalf of a user via the X-QCrBox-User header. The header is ignored
    # unless a token is configured and the request's X-QCrBox-Service-Token
    # matches.
    service_token: str | None = None
    # Trust the Remote-User header injected by Authelia for requests arriving
    # via Traefik.
    trust_remote_user_headers: bool = True
    # When set, Remote-User is only trusted if the request also carries a
    # matching X-QCrBox-Gateway-Token (injected by a Traefik headers
    # middleware), preventing containers on the docker network from forging
    # identities by calling the registry directly.
    gateway_token: str | None = None


class TestingSettings(QCrBoxSettingsBaseModel):
    # report_coverage: bool = False
    use_in_memory_db: bool = False
    use_real_rabbitmq_broker: bool = False


class CLISettings(QCrBoxSettingsBaseModel):
    disable_rich: bool = False


class StructlogRendererEnum(Enum):
    CONSOLE = "console"
    JSON = "json"


class LoggingSettings(QCrBoxSettingsBaseModel):
    log_func_entry_exit: bool = True
    log_level: str = "DEBUG" if IS_RUNNING_DEBUG_MODE or IS_RUNNING_INSIDE_TESTS else "INFO"
    renderer: StructlogRendererEnum = StructlogRendererEnum.JSON

    @property
    def log_level_as_int(self):
        return get_log_level_as_int(self.log_level)


class QCrBoxSettings(QCrBoxSettingsBaseModel):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=[".env.local"],
        env_nested_delimiter="__",
        env_prefix="QCRBOX__",
    )

    debug_mode: bool = IS_RUNNING_DEBUG_MODE
    nats: NATSSettings = NATSSettings()
    registry: RegistrySettings = RegistrySettings()
    orchestrator: OrchestratorSettings = OrchestratorSettings()
    auth: AuthSettings = AuthSettings()
    db: DatabaseSettings = DatabaseSettings()
    testing: TestingSettings = TestingSettings()
    cli: CLISettings = CLISettings()
    logging: LoggingSettings = LoggingSettings()


settings = QCrBoxSettings()
