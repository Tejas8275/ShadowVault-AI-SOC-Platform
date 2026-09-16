"""Versioned upgrades with explicit, validated adoption of unversioned Phase 1 data."""
import argparse
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect
from app.core.config import BACKEND_DIR, Settings
from app.db.session import build_engine


def migration_config(connection=None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def validate_phase1(connection) -> None:
    if connection.dialect.name != "sqlite":
        raise RuntimeError("Automatic Phase 1 adoption is verified only for SQLite")
    baseline_engine = create_engine("sqlite://")
    try:
        with baseline_engine.begin() as baseline:
            command.upgrade(migration_config(baseline), "0001")
            expected = MetaData()
            expected.reflect(baseline, only=["users", "incidents", "evidence", "timeline_events"])
            actual = inspect(connection)
            if set(actual.get_table_names()) != set(expected.tables):
                raise RuntimeError("Database is not an unversioned Phase 1 schema; adoption refused")
            if compare_metadata(MigrationContext.configure(connection), expected):
                raise RuntimeError("Phase 1 schema differs from the baseline; adoption refused")
            for table in expected.tables:
                def checks(inspector):
                    return {(item['name'], ' '.join(item['sqltext'].split()))
                            for item in inspector.get_check_constraints(table)}
                if checks(actual) != checks(inspect(baseline)):
                    raise RuntimeError("Phase 1 check constraints differ; adoption refused")
            if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Database has orphaned references; adoption refused")
    finally:
        baseline_engine.dispose()


def upgrade_database(settings: Settings | None = None, *, adopt_phase1=False) -> None:
    engine = build_engine(settings or Settings())
    try:
        with engine.connect() as connection:
            # Explicit BEGIN includes SQLite DDL in rollback on migration failure.
            if connection.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN")
            config = migration_config(connection)
            tables = inspect(connection).get_table_names()
            if tables and "alembic_version" not in tables:
                if not adopt_phase1:
                    raise RuntimeError("Unversioned database: back up, then use --adopt-phase1")
                validate_phase1(connection)
                command.stamp(config, "0001")
            command.upgrade(config, "head")
            connection.commit()
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt-phase1", action="store_true")
    args = parser.parse_args()
    upgrade_database(adopt_phase1=args.adopt_phase1)
    print("Database upgraded to the current migration revision.")
